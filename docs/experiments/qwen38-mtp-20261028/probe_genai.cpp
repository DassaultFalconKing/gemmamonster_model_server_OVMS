#include <openvino/genai/continuous_batching_pipeline.hpp>
#include <openvino/genai/llm_pipeline.hpp>
#include <iostream>
#include <chrono>
#include <fstream>

// Diagnostic only: mirrors OVMS CB initialization without its VLM draft gate.
int main(int argc, char** argv) {
    try {
        const std::filesystem::path model = "C:/llm/models/OpenVINO/Qwen3.8-27B-int4-ov";
        ov::genai::SchedulerConfig scheduler;
        scheduler.enable_prefix_caching = false;
        scheduler.max_num_seqs = 1;
        scheduler.max_num_batched_tokens = 16384;
        scheduler.cache_size = 0;
        ov::AnyMap properties{{"KV_CACHE_PRECISION", "u4"}, {"DYNAMIC_QUANTIZATION_GROUP_SIZE", 128}};
        if (argc > 1 && std::string(argv[1]) == "mtp") {
            std::cout << "DRAFT_BEGIN" << std::endl;
            properties.insert(ov::genai::draft_model(model, "GPU", ov::genai::scheduler_config(scheduler)));
            std::cout << "DRAFT_READY" << std::endl;
        }
        std::cout << "CB_BEGIN" << std::endl;
        ov::genai::ContinuousBatchingPipeline pipeline(model, scheduler, "GPU", properties);
        std::cout << "CB_READY" << std::endl;
        ov::genai::GenerationConfig config;
        config.max_new_tokens = 64;
        config.do_sample = false;
        config.apply_chat_template = false;
        const bool mtp = argc > 1 && std::string(argv[1]) == "mtp";
        const std::string mode = mtp ? "mtp" : "baseline";
        const auto lookaheads = mtp ? std::vector<size_t>{1, 2, 3, 5, 8} : std::vector<size_t>{0};
        const std::string root = "C:/gm/qwenmonster/benchmarks/qwen38-mtp-20261028/runs/native-" + mode;
        std::ofstream csv(root + ".csv");
        csv << "mode,nat,rep,seconds,tokens,status,finish_reason\n";
        for (auto nat : lookaheads) {
            if (mtp) config.num_assistant_tokens = nat;
            for (int rep = -2; rep < 5; ++rep) {
                const auto start = std::chrono::steady_clock::now();
                auto results = pipeline.generate(std::vector<std::string>{"<|im_start|>user\nExplain how a CPU cache improves program performance in one detailed paragraph.<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n"}, {config});
                const double seconds = std::chrono::duration<double>(std::chrono::steady_clock::now() - start).count();
                for (auto& result : results) {
                    const int finish = result.m_finish_reasons.empty() ? -1 : static_cast<int>(result.m_finish_reasons.front());
                    csv << mode << ',' << nat << ',' << rep << ',' << seconds << ',' << result.perf_metrics.get_num_generated_tokens() << ',' << static_cast<int>(result.m_status) << ',' << finish << std::endl;
                    std::cout << "RUN " << mode << " nat=" << nat << " rep=" << rep << " seconds=" << seconds << " tokens=" << result.perf_metrics.get_num_generated_tokens() << " status=" << static_cast<int>(result.m_status) << std::endl;
                    std::ofstream output(root + "-nat" + std::to_string(nat) + "-rep" + std::to_string(rep) + ".txt");
                    for (const auto& text : result.m_generation_ids) output << text;
                    // Some synchronous GenAI overloads leave m_status at its default RUNNING.
                    // Retain raw status/finish fields; validate output/token counts separately.
                    if (result.m_generation_ids.empty() || result.m_generation_ids.front().empty()) return 2;
                }
            }
        }
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "PROBE_FAIL: " << error.what() << std::endl;
        return 1;
    }
}
