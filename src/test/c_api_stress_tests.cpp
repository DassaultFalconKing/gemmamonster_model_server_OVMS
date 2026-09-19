//*****************************************************************************
// Copyright 2023 Intel Corporation
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
//*****************************************************************************
#include <atomic>
#include <chrono>
#include <functional>
#include <future>
#include <mutex>
#include <regex>
#include <sstream>
#include <thread>
#include <vector>

#include <gmock/gmock.h>
#include <gtest/gtest.h>

#include "../capi_frontend/buffer.hpp"
#include "../capi_frontend/capi_utils.hpp"
#include "../capi_frontend/inferenceresponse.hpp"
#include "../capi_frontend/servablemetadata.hpp"
#include "../config.hpp"
#include "../dags/pipeline.hpp"
#include "../dags/pipeline_factory.hpp"
#include "../dags/pipelinedefinition.hpp"
#include "src/filesystem/localfilesystem.hpp"
#include "../logging.hpp"
#include "../modelconfig.hpp"
#include "../modelinstance.hpp"
#include "../prediction_service_utils.hpp"
#include "src/servable_management/servablemanagermodule.hpp"
#include "../server.hpp"
#include "../status.hpp"
#include "../stringutils.hpp"
#include "c_api_test_utils.hpp"
#include "stress_test_utils.hpp"
#include "test_utils.hpp"

using namespace ovms;

static const char* stressTestPipelineOneDummyConfigSpecificVersionUsed = R"(
{
    "model_config_list": [
        {
            "config": {
                "name": "dummy",
                "base_path": "/ovms/src/test/dummy",
                "target_device": "CPU",
                "model_version_policy": {"latest": {"num_versions":1}},
                "nireq": 100,
                "shape": {"b": "(1,10) "}
            }
        }
    ],
    "pipeline_config_list": [
        {
            "name": "pipeline1Dummy",
            "inputs": ["custom_dummy_input"],
            "nodes": [
                {
                    "name": "dummyNode",
                    "model_name": "dummy",
                    "version": 1,
                    "type": "DL model",
                    "inputs": [
                        {"b": {"node_name": "request",
                               "data_item": "custom_dummy_input"}}
                    ],
                    "outputs": [
                        {"data_item": "a",
                         "alias": "new_dummy_output"}
                    ]
                }
            ],
            "outputs": [
                {"custom_dummy_output": {"node_name": "dummyNode",
                                         "data_item": "new_dummy_output"}
                }
            ]
        }
    ]
})";

using testing::_;
using testing::Return;

namespace {
struct AsyncStressWorkerState {
    std::atomic<bool> failed{false};
    std::mutex messageMutex;
    std::string message;

    void fail(std::string failureMessage) {
        bool expected = false;
        if (failed.compare_exchange_strong(expected, true)) {
            std::lock_guard<std::mutex> lock(messageMutex);
            message = std::move(failureMessage);
        }
    }

    std::string getMessage() {
        std::lock_guard<std::mutex> lock(messageMutex);
        return message;
    }
};

StatusCode consumeCapiStatus(OVMS_Status* status) {
    if (status == nullptr) {
        return StatusCode::OK;
    }

    uint32_t code = 0;
    OVMS_Status* codeStatus = OVMS_StatusCode(status, &code);
    if (codeStatus != nullptr) {
        OVMS_StatusDelete(codeStatus);
        OVMS_StatusDelete(status);
        return StatusCode::UNKNOWN_ERROR;
    }

    OVMS_StatusDelete(status);
    return static_cast<StatusCode>(code);
}

bool requireCapiOk(OVMS_Status* status, const char* operation, AsyncStressWorkerState& workerState) {
    auto code = consumeCapiStatus(status);
    if (code == StatusCode::OK) {
        return true;
    }
    workerState.fail(std::string(operation) + " failed: " + ovms::Status(code).string());
    return false;
}

struct AsyncStressCallbackState {
    std::promise<uint32_t> signal;
    AsyncStressWorkerState* workerState{nullptr};
};

void windowsSafeAsyncStressCallback(OVMS_InferenceResponse* response, uint32_t, void* userStruct) {
    auto* callbackState = reinterpret_cast<AsyncStressCallbackState*>(userStruct);
    OVMS_InferenceResponseDelete(response);
    try {
        callbackState->signal.set_value(42);
    } catch (const std::exception& e) {
        callbackState->workerState->fail(std::string("async completion signal failed: ") + e.what());
    } catch (...) {
        callbackState->workerState->fail("async completion signal failed with unknown exception");
    }
}

void runWindowsSafeAsyncWorker(
    OVMS_Server* cserver,
    std::future<void>& startSignal,
    std::future<void>& stopSignal,
    const std::set<StatusCode>& requiredLoadResults,
    const std::set<StatusCode>& allowedLoadResults,
    std::unordered_map<StatusCode, std::atomic<uint64_t>>& retCodeCounters,
    int stressIterationsLimit,
    AsyncStressWorkerState& workerState) {
    startSignal.get();
    auto stressIterationsCounter = stressIterationsLimit;
    bool breakLoop = false;

    while (stressIterationsCounter-- > 0) {
        if (workerState.failed.load()) {
            break;
        }
        if (breakLoop) {
            break;
        }
        if (stopSignal.wait_for(std::chrono::milliseconds(0)) == std::future_status::ready) {
            breakLoop = true;
        }

        OVMS_InferenceRequest* request{nullptr};
        if (!requireCapiOk(OVMS_InferenceRequestNew(&request, cserver, "dummy", 1), "OVMS_InferenceRequestNew", workerState) || request == nullptr) {
            if (request == nullptr && !workerState.failed.load()) {
                workerState.fail("OVMS_InferenceRequestNew returned a null request");
            }
            break;
        }

        if (!requireCapiOk(OVMS_InferenceRequestAddInput(request, "b", OVMS_DATATYPE_FP32, DUMMY_MODEL_SHAPE.data(), DUMMY_MODEL_SHAPE.size()), "OVMS_InferenceRequestAddInput", workerState)) {
            OVMS_InferenceRequestDelete(request);
            break;
        }

        std::array<float, DUMMY_MODEL_INPUT_SIZE> data{0, 1, 2, 3, 4, 5, 6, 7, 8, 9};
        if (!requireCapiOk(OVMS_InferenceRequestInputSetData(request, "b", reinterpret_cast<void*>(data.data()), sizeof(float) * data.size(), OVMS_BUFFERTYPE_CPU, 0), "OVMS_InferenceRequestInputSetData", workerState)) {
            OVMS_InferenceRequestDelete(request);
            break;
        }

        AsyncStressCallbackState callbackState;
        callbackState.workerState = &workerState;
        auto unblockSignal = callbackState.signal.get_future();
        if (!requireCapiOk(OVMS_InferenceRequestSetCompletionCallback(request, windowsSafeAsyncStressCallback, reinterpret_cast<void*>(&callbackState)), "OVMS_InferenceRequestSetCompletionCallback", workerState)) {
            OVMS_InferenceRequestDelete(request);
            break;
        }

        OVMS_Status* rawStatus = OVMS_InferenceAsync(cserver, request);
        const bool scheduled = rawStatus == nullptr;
        const auto statusCode = consumeCapiStatus(rawStatus);

        if (scheduled) {
            try {
                if (unblockSignal.get() != 42) {
                    workerState.fail("unexpected async completion signal value");
                }
            } catch (const std::exception& e) {
                workerState.fail(std::string("async completion wait failed: ") + e.what());
            } catch (...) {
                workerState.fail("async completion wait failed with unknown exception");
            }
        }

        OVMS_InferenceRequestDelete(request);
        retCodeCounters.at(statusCode).fetch_add(1);

        if (requiredLoadResults.find(statusCode) == requiredLoadResults.end() &&
            allowedLoadResults.find(statusCode) == allowedLoadResults.end()) {
            workerState.fail(std::string("unexpected async inference status: ") + ovms::Status(statusCode).string());
        }
    }

    if (stressIterationsCounter <= 0 && !workerState.failed.load()) {
        workerState.fail("stress worker exhausted its iteration budget before the stop signal");
    }
}

void runWindowsSafeAsyncStress(
    OVMS_Server* cserver,
    ModelManager* manager,
    const std::string& initialConfig,
    const std::string& configFilePath,
    const std::function<void()>& configChangeOperation,
    bool reloadWholeConfig,
    const std::set<StatusCode>& requiredLoadResults,
    const std::set<StatusCode>& allowedLoadResults,
    uint32_t loadThreadCount,
    uint32_t beforeConfigChangeLoadTimeMs,
    uint32_t afterConfigChangeLoadTimeMs,
    int stressIterationsLimit) {
    createConfigFileWithContent(initialConfig, configFilePath);
    auto initialStatus = manager->startFromFile(configFilePath);
    ASSERT_TRUE(initialStatus.ok()) << initialStatus.string();

    std::vector<std::promise<void>> startSignals(loadThreadCount);
    std::vector<std::promise<void>> stopSignals(loadThreadCount);
    std::vector<std::future<void>> futureStartSignals;
    std::vector<std::future<void>> futureStopSignals;
    futureStartSignals.reserve(loadThreadCount);
    futureStopSignals.reserve(loadThreadCount);
    for (auto& signal : startSignals) {
        futureStartSignals.emplace_back(signal.get_future());
    }
    for (auto& signal : stopSignals) {
        futureStopSignals.emplace_back(signal.get_future());
    }

    std::unordered_map<StatusCode, std::atomic<uint64_t>> retCodeCounters;
    for (uint32_t i = 0; i != static_cast<uint32_t>(StatusCode::STATUS_CODE_END); ++i) {
        retCodeCounters[static_cast<StatusCode>(i)] = 0;
    }

    AsyncStressWorkerState workerState;
    std::vector<std::thread> workerThreads;
    workerThreads.reserve(loadThreadCount);
    for (uint32_t i = 0; i < loadThreadCount; ++i) {
        workerThreads.emplace_back([&, i]() {
            runWindowsSafeAsyncWorker(
                cserver,
                futureStartSignals[i],
                futureStopSignals[i],
                requiredLoadResults,
                allowedLoadResults,
                retCodeCounters,
                stressIterationsLimit,
                workerState);
        });
    }

    for (auto& signal : startSignals) {
        signal.set_value();
    }
    std::this_thread::sleep_for(std::chrono::milliseconds(beforeConfigChangeLoadTimeMs));
    configChangeOperation();
    auto reloadStatus = reloadWholeConfig ? manager->startFromFile(configFilePath) : manager->updateConfigurationWithoutConfigFile();
    std::this_thread::sleep_for(std::chrono::milliseconds(afterConfigChangeLoadTimeMs));
    for (auto& signal : stopSignals) {
        signal.set_value();
    }
    for (auto& worker : workerThreads) {
        worker.join();
    }

    ASSERT_TRUE(reloadStatus.ok()) << reloadStatus.string();
    ASSERT_FALSE(workerState.failed.load()) << workerState.getMessage();

    for (auto& [retCode, counter] : retCodeCounters) {
        if (requiredLoadResults.find(retCode) != requiredLoadResults.end()) {
            EXPECT_GT(counter.load(), 0) << static_cast<uint32_t>(retCode) << ":" << ovms::Status(retCode).string() << " did not occur. This may indicate fail or fail in test setup";
            continue;
        }
        if (counter.load() == 0) {
            continue;
        }
        EXPECT_TRUE(allowedLoadResults.find(retCode) != allowedLoadResults.end()) << "Ret code:"
                                                                                 << static_cast<uint32_t>(retCode) << " message: " << ovms::Status(retCode).string()
                                                                                 << " was not allowed in test but occurred during load";
    }
}
}  // namespace

class StressCapiConfigChanges : public ConfigChangeStressTest {
public:
    void SetUp() override {
#ifdef _WIN32
        GTEST_SKIP() << "Skipping test on Windows, sporadic";  // CVS-176244
#endif
        ConfigChangeStressTest::SetUp();
    }
};

class ConfigChangeStressTestSingleModel : public ConfigChangeStressTestAsync {
public:
    void SetUp() override {
#ifdef _WIN32
        GTEST_SKIP() << "Skipping test on Windows, sporadic";  // CVS-176244
#endif
        ConfigChangeStressTestAsync::SetUp();
    }
};

class StressModelCapiConfigChanges : public StressCapiConfigChanges {
    const std::string modelName = "dummy";
    const std::string modelInputName = "b";
    const std::string modelOutputName = "a";

public:
    std::string getServableName() override {
        return modelName;
    }
    void SetUp() override {
        SetUpCAPIServerInstance(initialClearConfig);
    }
};

TEST_F(ConfigChangeStressTestSingleModel, ChangeToEmptyConfigInference) {
    bool performWholeConfigReload = true;  // we just need to have all model versions rechecked
    std::set<StatusCode> requiredLoadResults = {
        StatusCode::OK,
        StatusCode::MODEL_VERSION_NOT_LOADED_ANYMORE};  // we expect full continuity of operation
    std::set<StatusCode> allowedLoadResults = {};
    performStressTest(
        &ConfigChangeStressTest::triggerCApiInferenceInALoopSingleModel,
        &ConfigChangeStressTest::changeToEmptyConfig,
        performWholeConfigReload,
        requiredLoadResults,
        allowedLoadResults);
}

TEST_F(ConfigChangeStressTestAsync, ChangeToEmptyConfigAsyncInference) {
    bool performWholeConfigReload = true;
    std::set<StatusCode> requiredLoadResults = {
        StatusCode::OK,
        StatusCode::MODEL_VERSION_NOT_LOADED_ANYMORE};
    std::set<StatusCode> allowedLoadResults = {};
    runWindowsSafeAsyncStress(
        cserver,
        manager,
        ovmsConfig,
        configFilePath,
        [this]() { changeToEmptyConfig(); },
        performWholeConfigReload,
        requiredLoadResults,
        allowedLoadResults,
        loadThreadCount,
        beforeConfigChangeLoadTimeMs,
        afterConfigChangeLoadTimeMs,
        stressIterationsLimit);
}

TEST_F(ConfigChangeStressTestAsync, ChangeToWrongShapeAsyncInference) {
    bool performWholeConfigReload = true;
    std::set<StatusCode> requiredLoadResults = {StatusCode::OK};
    std::set<StatusCode> allowedLoadResults = {StatusCode::INVALID_SHAPE};
    runWindowsSafeAsyncStress(
        cserver,
        manager,
        ovmsConfig,
        configFilePath,
        [this]() { changeToWrongShapeOneModel(); },
        performWholeConfigReload,
        requiredLoadResults,
        allowedLoadResults,
        loadThreadCount,
        beforeConfigChangeLoadTimeMs,
        afterConfigChangeLoadTimeMs,
        stressIterationsLimit);
}

TEST_F(ConfigChangeStressTestAsync, ChangeToAutoShapeDuringAsyncInference) {
    bool performWholeConfigReload = true;
    std::set<StatusCode> requiredLoadResults = {StatusCode::OK};
    std::set<StatusCode> allowedLoadResults = {StatusCode::MODEL_VERSION_NOT_LOADED_YET};
    runWindowsSafeAsyncStress(
        cserver,
        manager,
        ovmsConfig,
        configFilePath,
        [this]() { changeToAutoShapeOneModel(); },
        performWholeConfigReload,
        requiredLoadResults,
        allowedLoadResults,
        loadThreadCount,
        beforeConfigChangeLoadTimeMs,
        afterConfigChangeLoadTimeMs,
        stressIterationsLimit);
}

TEST_F(ConfigChangeStressTestAsyncStartEmpty, ChangeToLoadedModelDuringAsyncInference) {
    bool performWholeConfigReload = true;
    std::set<StatusCode> requiredLoadResults = {StatusCode::OK};
    std::set<StatusCode> allowedLoadResults = {
        StatusCode::PIPELINE_DEFINITION_NAME_MISSING,
        StatusCode::MODEL_NAME_MISSING,
        StatusCode::MODEL_VERSION_MISSING};
    runWindowsSafeAsyncStress(
        cserver,
        manager,
        ovmsConfig,
        configFilePath,
        [this]() { addFirstModel(); },
        performWholeConfigReload,
        requiredLoadResults,
        allowedLoadResults,
        loadThreadCount,
        beforeConfigChangeLoadTimeMs,
        afterConfigChangeLoadTimeMs,
        stressIterationsLimit);
}

TEST_F(StressCapiConfigChanges, AddNewVersionDuringPredictLoad) {
    bool performWholeConfigReload = false;                        // we just need to have all model versions rechecked
    std::set<StatusCode> requiredLoadResults = {StatusCode::OK};  // we expect full continuity of operation
    std::set<StatusCode> allowedLoadResults = {};
    performStressTest(
        &StressCapiConfigChanges::triggerCApiInferenceInALoop,
        &StressCapiConfigChanges::defaultVersionAdd,
        performWholeConfigReload,
        requiredLoadResults,
        allowedLoadResults);
}
TEST_F(StressCapiConfigChanges, KFSAddNewVersionDuringPredictLoad) {
    bool performWholeConfigReload = false;                        // we just need to have all model versions rechecked
    std::set<StatusCode> requiredLoadResults = {StatusCode::OK};  // we expect full continuity of operation
    std::set<StatusCode> allowedLoadResults = {};
    performStressTest(
        &StressCapiConfigChanges::triggerCApiInferenceInALoop,
        &StressCapiConfigChanges::defaultVersionAdd,
        performWholeConfigReload,
        requiredLoadResults,
        allowedLoadResults);
}

TEST_F(StressCapiConfigChanges, DISABLED_GetMetricsDuringLoad) {
    bool performWholeConfigReload = false;                        // we just need to have all model versions rechecked
    std::set<StatusCode> requiredLoadResults = {StatusCode::OK};  // we expect full continuity of operation
    std::set<StatusCode> allowedLoadResults = {};
    performStressTest(
        &StressCapiConfigChanges::triggerCApiInferenceInALoop,
        &StressCapiConfigChanges::testCurrentRequestsMetric,
        performWholeConfigReload,
        requiredLoadResults,
        allowedLoadResults);
}
TEST_F(StressCapiConfigChanges, RemoveDefaultVersionDuringPredictLoad) {
    std::set<StatusCode> requiredLoadResults = {StatusCode::OK,
        StatusCode::PIPELINE_DEFINITION_NOT_LOADED_YET,
        StatusCode::MODEL_VERSION_MISSING};
    std::set<StatusCode> allowedLoadResults = {StatusCode::MODEL_VERSION_NOT_LOADED_ANYMORE};
    bool performWholeConfigReload = true;
    performStressTest(
        &StressCapiConfigChanges::triggerCApiInferenceInALoop,
        &StressCapiConfigChanges::defaultVersionRemove,
        performWholeConfigReload,
        requiredLoadResults,
        allowedLoadResults);
}
TEST_F(StressCapiConfigChanges, ChangeToShapeAutoDuringPredictLoad) {
    bool performWholeConfigReload = true;
    std::set<StatusCode> requiredLoadResults = {StatusCode::OK};
    std::set<StatusCode> allowedLoadResults = {StatusCode::PIPELINE_DEFINITION_NOT_LOADED_YET};
    performStressTest(
        &StressCapiConfigChanges::triggerCApiInferenceInALoop,
        &StressCapiConfigChanges::changeToAutoShape,
        performWholeConfigReload,
        requiredLoadResults,
        allowedLoadResults);
}
TEST_F(StressCapiConfigChanges, RemovePipelineDefinitionDuringPredictLoad) {
    bool performWholeConfigReload = true;
    std::set<StatusCode> requiredLoadResults = {StatusCode::OK,
        StatusCode::PIPELINE_DEFINITION_NOT_LOADED_ANYMORE};
    std::set<StatusCode> allowedLoadResults = {};
    performStressTest(
        &StressCapiConfigChanges::triggerCApiInferenceInALoop,
        &StressCapiConfigChanges::removePipelineDefinition,
        performWholeConfigReload,
        requiredLoadResults,
        allowedLoadResults);
}
TEST_F(StressCapiConfigChanges, ChangedPipelineConnectionNameDuringPredictLoad) {
    bool performWholeConfigReload = true;
    std::set<StatusCode> requiredLoadResults = {StatusCode::OK};
    std::set<StatusCode> allowedLoadResults = {StatusCode::PIPELINE_DEFINITION_NOT_LOADED_YET};
    performStressTest(
        &StressCapiConfigChanges::triggerCApiInferenceInALoop,
        &StressCapiConfigChanges::changeConnectionName,
        performWholeConfigReload,
        requiredLoadResults,
        allowedLoadResults);
}
TEST_F(StressCapiConfigChanges, AddedNewPipelineDuringPredictLoad) {
    bool performWholeConfigReload = true;
    std::set<StatusCode> requiredLoadResults = {StatusCode::OK};
    std::set<StatusCode> allowedLoadResults = {};
    performStressTest(
        &StressCapiConfigChanges::triggerCApiInferenceInALoop,
        &StressCapiConfigChanges::addNewPipeline,
        performWholeConfigReload,
        requiredLoadResults,
        allowedLoadResults);
}
TEST_F(StressCapiConfigChanges, RetireSpecificVersionUsedDuringPredictLoad) {
    SetUpConfig(stressTestPipelineOneDummyConfigSpecificVersionUsed);
    bool performWholeConfigReload = false;
    std::set<StatusCode> requiredLoadResults = {StatusCode::OK,
        StatusCode::PIPELINE_DEFINITION_NOT_LOADED_YET};
    std::set<StatusCode> allowedLoadResults = {StatusCode::MODEL_VERSION_NOT_LOADED_ANYMORE};
    performStressTest(
        &StressCapiConfigChanges::triggerCApiInferenceInALoop,
        &StressCapiConfigChanges::retireSpecificVersionUsed,
        performWholeConfigReload,
        requiredLoadResults,
        allowedLoadResults);
}
TEST_F(StressCapiConfigChanges, AddNewVersionDuringGetMetadataLoad) {
    bool performWholeConfigReload = false;
    std::set<StatusCode> requiredLoadResults = {StatusCode::OK};
    std::set<StatusCode> allowedLoadResults = {};
    performStressTest(
        &StressCapiConfigChanges::triggerCApiGetMetadataInALoop,
        &StressCapiConfigChanges::defaultVersionAdd,
        performWholeConfigReload,
        requiredLoadResults,
        allowedLoadResults);
}
TEST_F(StressCapiConfigChanges, RemoveDefaultVersionDuringGetMetadataLoad) {
    std::set<StatusCode> requiredLoadResults = {StatusCode::OK,
        StatusCode::PIPELINE_DEFINITION_NOT_LOADED_YET};
    std::set<StatusCode> allowedLoadResults = {};
    bool performWholeConfigReload = true;
    performStressTest(
        &StressCapiConfigChanges::triggerCApiGetMetadataInALoop,
        &StressCapiConfigChanges::defaultVersionRemove,
        performWholeConfigReload,
        requiredLoadResults,
        allowedLoadResults);
}
TEST_F(StressCapiConfigChanges, ChangeToShapeAutoDuringGetMetadataLoad) {
    bool performWholeConfigReload = true;
    std::set<StatusCode> requiredLoadResults = {StatusCode::OK};
    std::set<StatusCode> allowedLoadResults = {StatusCode::PIPELINE_DEFINITION_NOT_LOADED_YET};
    performStressTest(
        &StressCapiConfigChanges::triggerCApiGetMetadataInALoop,
        &StressCapiConfigChanges::changeToAutoShape,
        performWholeConfigReload,
        requiredLoadResults,
        allowedLoadResults);
}
TEST_F(StressCapiConfigChanges, RemovePipelineDefinitionDuringGetMetadataLoad) {
    bool performWholeConfigReload = true;
    std::set<StatusCode> requiredLoadResults = {StatusCode::OK,
        StatusCode::PIPELINE_DEFINITION_NOT_LOADED_ANYMORE};
    std::set<StatusCode> allowedLoadResults = {};
    performStressTest(
        &StressCapiConfigChanges::triggerCApiGetMetadataInALoop,
        &StressCapiConfigChanges::removePipelineDefinition,
        performWholeConfigReload,
        requiredLoadResults,
        allowedLoadResults);
}
TEST_F(StressCapiConfigChanges, ChangedPipelineConnectionNameDuringGetMetadataLoad) {
    bool performWholeConfigReload = true;
    std::set<StatusCode> requiredLoadResults = {StatusCode::OK};
    std::set<StatusCode> allowedLoadResults = {StatusCode::PIPELINE_DEFINITION_NOT_LOADED_YET};
    performStressTest(
        &StressCapiConfigChanges::triggerCApiGetMetadataInALoop,
        &StressCapiConfigChanges::changeConnectionName,
        performWholeConfigReload,
        requiredLoadResults,
        allowedLoadResults);
}
TEST_F(StressCapiConfigChanges, AddedNewPipelineDuringGetMetadataLoad) {
    bool performWholeConfigReload = true;
    std::set<StatusCode> requiredLoadResults = {StatusCode::OK};
    std::set<StatusCode> allowedLoadResults = {};
    performStressTest(
        &StressCapiConfigChanges::triggerCApiGetMetadataInALoop,
        &StressCapiConfigChanges::addNewPipeline,
        performWholeConfigReload,
        requiredLoadResults,
        allowedLoadResults);
}
TEST_F(StressCapiConfigChanges, RetireSpecificVersionUsedDuringGetMetadataLoad) {
    SetUpConfig(stressTestPipelineOneDummyConfigSpecificVersionUsed);
    bool performWholeConfigReload = false;
    std::set<StatusCode> requiredLoadResults = {StatusCode::OK,
        StatusCode::PIPELINE_DEFINITION_NOT_LOADED_YET};
    std::set<StatusCode> allowedLoadResults = {};
    performStressTest(
        &StressCapiConfigChanges::triggerCApiGetMetadataInALoop,
        &StressCapiConfigChanges::retireSpecificVersionUsed,
        performWholeConfigReload,
        requiredLoadResults,
        allowedLoadResults);
}

TEST_F(StressCapiConfigChanges, AddModelDuringGetModelStatusLoad) {
    bool performWholeConfigReload = true;
    std::set<StatusCode> requiredLoadResults = {StatusCode::OK};
    std::set<StatusCode> allowedLoadResults = {StatusCode::MODEL_VERSION_MISSING};
    performStressTest(
        &ConfigChangeStressTest::triggerCApiGetStatusInALoop,
        &ConfigChangeStressTest::addFirstModel,
        performWholeConfigReload,
        requiredLoadResults,
        allowedLoadResults);
}
