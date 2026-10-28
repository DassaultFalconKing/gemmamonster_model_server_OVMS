#include <openvino/genai/continuous_batching_pipeline.hpp>
#include <openvino/genai/llm_pipeline.hpp>
#include <fstream>
#include <iostream>
#include <chrono>

int main(int argc, char** argv) {
    try {
        if (argc != 6) throw std::runtime_error("mode kv dq key_mode output_prefix required");
        const bool mtp = std::string(argv[1]) == "mtp";
        const std::filesystem::path model = "C:/llm/models/OpenVINO/Qwen3.8-27B-int4-ov";
        const std::string root = argv[5];
        const std::string ids_path = "C:/gm/qwenmonster/benchmarks/qwen38-mtp-20261028/rca/input-ids.txt";
        ov::genai::Tokenizer tokenizer(model);
        std::vector<int64_t> ids;
        std::ifstream input(ids_path);
        int64_t token;
        if (input.good()) { while (input >> token) ids.push_back(token); }
        else {
            auto encoded = tokenizer.encode("<|im_start|>user\nExplain how a CPU cache improves program performance in one detailed paragraph.<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n");
            auto* data = encoded.input_ids.data<int64_t>();
            ids.assign(data, data + encoded.input_ids.get_size());
            std::ofstream output(ids_path);
            for (auto id : ids) output << id << '\n';
        }
        if (ids.empty()) throw std::runtime_error("empty input IDs");
        std::ofstream receipt(root + "-input-ids.txt");
        for (auto id : ids) receipt << id << '\n';
        receipt.close();
        const auto prompt = tokenizer.decode(ids, ov::genai::skip_special_tokens(false));
        auto roundtrip = tokenizer.encode(prompt);
        const auto* roundtrip_data = roundtrip.input_ids.data<int64_t>();
        if (std::vector<int64_t>(roundtrip_data, roundtrip_data + roundtrip.input_ids.get_size()) != ids)
            throw std::runtime_error("input ID roundtrip drift");
        ov::genai::SchedulerConfig scheduler;
        scheduler.enable_prefix_caching = false;
        scheduler.max_num_seqs = 1;
        scheduler.max_num_batched_tokens = 16384;
        scheduler.cache_size = 0;
        ov::AnyMap properties{{"KV_CACHE_PRECISION", std::string(argv[2])}, {"DYNAMIC_QUANTIZATION_GROUP_SIZE", std::stoi(argv[3])}};
        if (std::string(argv[4]) != "default") properties["KEY_CACHE_QUANT_MODE"] = std::string(argv[4]);
        if (mtp) properties.insert(ov::genai::draft_model(model, "GPU", ov::genai::scheduler_config(scheduler)));
        std::cout << "LOAD_BEGIN" << std::endl;
        ov::genai::ContinuousBatchingPipeline pipeline(model, scheduler, "GPU", properties);
        std::cout << "LOAD_READY" << std::endl;
        ov::genai::GenerationConfig config;
        config.max_new_tokens = 64;
        config.do_sample = false;
        config.apply_chat_template = false;
        config.rng_seed = 1234;
        if (mtp) config.num_assistant_tokens = 3;
        for (int rep = 0; rep < 2; ++rep) {
            const auto start = std::chrono::steady_clock::now();
            auto handle = pipeline.add_request(rep, prompt, config);
            while (pipeline.has_non_finished_requests()) pipeline.step();
            auto results = handle->read_all();
            if (results.size() != 1) throw std::runtime_error("unexpected result shape");
            const auto& generated = results.front().generated_ids;
            const int finish = static_cast<int>(results.front().finish_reason);
            std::ofstream output(root + "-rep" + std::to_string(rep) + ".json");
            output << "{\"seconds\":" << std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count()
                   << ",\"status\":" << static_cast<int>(handle->get_status()) << ",\"finish\":" << finish << ",\"ids\":[";
            for (size_t i=0; i<generated.size(); ++i) { if(i) output << ','; output << generated[i]; }
            output << "]}\n";
            std::ofstream text(root + "-rep" + std::to_string(rep) + ".txt");
            text << tokenizer.decode(generated);
            std::cout << "GENERATED rep=" << rep << " tokens=" << generated.size() << " finish=" << finish << std::endl;
        }
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "PROBE_FAIL: " << error.what() << std::endl;
        return 1;
    }
}
