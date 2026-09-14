from tokenizers import Tokenizer

t = Tokenizer.from_file(
    "C:\\llm\\models\\OpenVINO\\Wondernutts\\"
    "gemma-4-26B-A4B-it-qat-q4_0-unquantized-uncensored-heretic-int4-ov\\"
    "tokenizer.json"
)
ids = [48, 6639, 236787, 17454, 236782, 107, 236775, 1005, 1083, 107,
       236775, 167729, 236772, 1582, 236772, 236812, 236775, 107,
       236783, 49, 50]
print("n_ids:", len(ids))
print("decode(skip_special_tokens=False):")
print(repr(t.decode(ids, skip_special_tokens=False)))
print("decode(skip_special_tokens=True):")
print(repr(t.decode(ids, skip_special_tokens=True)))
print("per-token:")
for i in ids:
    print(i, repr(t.decode([i], skip_special_tokens=False)))
dec = t.get_added_tokens_decoder()
print("num_added_tokens:", len(dec))
for k in sorted(dec):
    print(k, repr(dec[k].content), "special=", dec[k].special)
