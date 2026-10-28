from pathlib import Path
root = Path(r"C:\gm\qwenmonster\benchmarks\qwen38-mtp-20261028\rca\source\openvino.genai-5f7f1278107d7eae3990ce906bbcfcb69ac3397f")
path = root / "src/cpp/src/visual_language/inputs_embedder.cpp"
source = path.read_text()
assert "RCA_TRACE_DIR" not in source
source = '#include <atomic>\n#include <cstdlib>\n#include <fstream>\n' + source
needle = '    auto new_input_ids = update_history(new_chat_tokens);'
assert source.count(needle) == 1
source = source.replace(needle, needle + r'''
    if (const char* directory = std::getenv("RCA_TRACE_DIR")) {
        static std::atomic<uint64_t> input_counter{0};
        std::ofstream receipt(std::string(directory) + "/input-" + std::to_string(input_counter.fetch_add(1)) + ".txt");
        const auto* data = new_input_ids.data<int64_t>();
        for (size_t i=0; i<new_input_ids.get_size(); ++i) receipt << data[i] << '\n';
    }
''')
path.write_text(source)
print(path)
