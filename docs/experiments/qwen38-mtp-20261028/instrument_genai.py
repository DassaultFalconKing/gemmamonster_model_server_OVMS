"""Add opt-in observation only to the exact downloaded GenAI source."""
from pathlib import Path
root = Path(r"C:\gm\qwenmonster\benchmarks\qwen38-mtp-20261028\rca\source\openvino.genai-5f7f1278107d7eae3990ce906bbcfcb69ac3397f")
path = root / "src/cpp/src/continuous_batching/pipeline_impl.cpp"
source = path.read_text()
assert "RCA_TRACE_DIR" not in source, "already instrumented"
source = source.replace("#include <atomic>", "#include <atomic>\n#include <cstdlib>\n#include <fstream>")
needle = "    // evict unimportant blocks from KV cache, if requested"
insert = r'''
    // RCA observer: no sampler, cache, scheduling or tensor modifications.
    static std::atomic<uint64_t> rca_event_counter{0};
    const char* rca_dir = std::getenv("RCA_TRACE_DIR");
    const uint64_t rca_event = rca_dir ? rca_event_counter.fetch_add(1) : 0;
    std::string rca_prefix;
    if (rca_dir && rca_event < 128) {
        rca_prefix = std::string(rca_dir) + "/event-" + std::to_string(rca_event);
        std::ofstream raw(rca_prefix + ".bin", std::ios::binary);
        raw.write(static_cast<const char*>(logits.data()), logits.get_byte_size());
    }
    auto rca_dump = [&](const char* stage) {
        if (rca_prefix.empty()) return;
        std::ofstream out(rca_prefix + "-" + stage + ".txt");
        out << "instance " << this << " validation " << m_is_validation_mode_enabled << " dtype " << logits.get_element_type() << " shape";
        for (auto dim : logits.get_shape()) out << ' ' << dim;
        out << '\n';
        for (const auto& group : m_requests) {
            out << "request " << group->get_request_id() << " processed " << group->get_num_processed_tokens()
                << " scheduled " << group->get_num_scheduled_tokens() << " output_len " << group->get_output_seq_len()
                << " validate " << group->get_num_tokens_to_validate() << " prompt";
            for (auto id : group->get_prompt_ids()) out << ' ' << id;
            out << '\n';
            for (const auto& sequence : group->get_sequences()) {
                out << "generated";
                for (auto id : sequence->get_generated_ids()) out << ' ' << id;
                out << '\n';
            }
        }
    };
    rca_dump("before");

'''
assert source.count(needle) == 1
source = source.replace(needle, insert + needle)
needle2 = "    // Promote the committed linear-attention state to the correct physical row"
assert source.count(needle2) == 1
source = source.replace(needle2, '    rca_dump("after-sample");\n\n' + needle2)
path.write_text(source)
print(path)
