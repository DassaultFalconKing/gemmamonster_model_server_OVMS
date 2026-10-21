# Qwen executable-argument validation

The parser now validates completed typed arguments with the existing RapidJSON
Draft 4 engine, after validating the tool schema against an embedded meta-schema.
Registry checking and lexical typed-value rejection remain separate earlier gates.
No property defaults are inserted. Duplicate XML parameter names reject the call.

The embedded source is JSON Schema's Draft 4 `schema.json` at
`json-schema-org/json-schema-spec@dba92b702c94858162f653590230e7573c8b7dd0`,
SHA256 `e1489d0b4755f02793302591d3fcb8f07b6893a82a94f24895f8e4edf11b82e2`.
It was located through the official website's `_includes/draft-04` submodule.
The original JSON and BSD notice are retained in `draft4_meta_schema.hpp`.
Validation never fetches network resources or reads a runtime schema file.

This is a restricted supported profile, not all JSON Schema dialects:

- Draft 4 types, integer/number distinction, required, enum, object/array
  constraints, additionalProperties, anyOf/oneOf/allOf/not and local references
  use RapidJSON's validator. Enum values are restricted to scalars because this
  RapidJSON revision also compiles enum objects as schemas.
- Unknown keywords (including newer `const`) reject the schema instead of being
  silently ignored. `format` is rejected because format assertions are not enabled.
- `$schema`, when present, must select the supported Draft 4 dialect.
- `$ref` is restricted to `#/definitions/NAME`, with ASCII letters, digits,
  underscore, period and hyphen in NAME. Every target is meta-validated as a
  schema. References into annotations, map containers, URI-escaped extra path
  segments and remote documents are rejected.
- Defaults may be scalar annotations. They are removed from schema-valued nodes
  before compilation because this RapidJSON revision otherwise lets string
  defaults satisfy a missing required property. A property named `default` is
  preserved. Composite defaults are rejected before compilation.
- Embedded NUL in schemas, names or argument strings is rejected, preventing
  C-string truncation in this engine's regex paths. Raw NUL in native parameter
  text is also rejected before JSON normalization.
- Duplicate JSON object names in schemas or typed arguments are rejected before
  validation. Duplicate defaults cannot survive annotation removal or weaken a
  required-field check.
- A preflight rejects non-object `patternProperties` anywhere in compiler input,
  including an otherwise valid property-dependency map with that member name.
  RapidJSON's recursive schema-map compilation assumes an object there.
- Empty `required: []` is accepted as the common tool-schema spelling of no
  required fields, including legitimate zero-parameter tools. The meta-schema's
  stringArray minimum is explicitly relaxed to zero for this profile.

The active table-driven regression exercises 36 valid/invalid schemas and native
XML payloads. It covers enums, integer versus number, nested arrays/objects,
nullable unions, anyOf, overlapping oneOf, extra properties, missing required
fields, duplicate XML names, malformed schemas, local and remote references,
unsupported dialects and unsupported keywords. Review regressions cover references
through annotations, unsafe dependency maps, NUL regex/arguments, ignored scalar
defaults, nested required defaults and a real parameter named `default`.
It passed after retained RED runs.
The normal zero-parameter parser control remains active and passing.

MSVC's `/WX` initially rejected RapidJSON diagnostics C5232 (intentional child
value recursion with C++20 rewritten comparisons) and C6313 (zero-valued template
flags, already suppressed in existing schema code). Suppressions are confined to
the third-party schema include. Nested/union runtime tests verify the instantiated
validator; no global warning or language-mode change was made.

This parser gate does not prove constrained-generation masks, a valid call for
every required request, correct reasoning-prefix transitions, or live model/API
acceptance. Unsupported tool schemas currently fail closed at publication; an
earlier request-level error remains a separate API usability improvement.
