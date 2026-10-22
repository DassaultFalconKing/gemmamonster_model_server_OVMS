//*****************************************************************************
// Copyright 2026 Intel Corporation
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at http://www.apache.org/licenses/LICENSE-2.0
//*****************************************************************************
#include "tool_schema_profile.hpp"

#include <atomic>
#include <cstring>
#include <unordered_set>
#include <utility>

#pragma warning(push)
// Match the existing Qwen restricted-schema compiler settings for MSVC.
#pragma warning(disable : 5232 6313)
#include "rapidjson/schema.h"
#pragma warning(pop)

#include "draft4_meta_schema.hpp"

namespace ovms {
namespace {
bool safeValidationInput(const rapidjson::Value& value, bool compilerInput) {
    if (value.IsString())
        return std::memchr(value.GetString(), '\0', value.GetStringLength()) == nullptr;
    if (value.IsArray()) {
        for (const auto& item : value.GetArray())
            if (!safeValidationInput(item, compilerInput)) return false;
    } else if (value.IsObject()) {
        std::unordered_set<std::string> names;
        for (const auto& member : value.GetObject()) {
            if (!safeValidationInput(member.name, compilerInput)) return false;
            if (!names.emplace(member.name.GetString(), member.name.GetStringLength()).second) return false;
            // RapidJSON recursively compiles schema-map containers too, and
            // assumes this member is object-valued even in a dependency map.
            if (compilerInput && std::strcmp(member.name.GetString(), "patternProperties") == 0 && !member.value.IsObject())
                return false;
            if (!safeValidationInput(member.value, compilerInput)) return false;
        }
    }
    return true;
}

void removeSchemaDefaults(rapidjson::Value& schema) {
    if (!schema.IsObject()) return;
    // Defaults are annotations, never a substitute for required values. Only
    // visit schema-valued locations; a property *named* default must survive.
    while (schema.HasMember("default")) schema.RemoveMember("default");
    for (const auto* key : {"properties", "patternProperties", "definitions", "dependencies"}) {
        if (schema.HasMember(key) && schema[key].IsObject())
            for (auto& member : schema[key].GetObject())
                removeSchemaDefaults(member.value);
    }
    for (const auto* key : {"additionalProperties", "additionalItems", "not"})
        if (schema.HasMember(key)) removeSchemaDefaults(schema[key]);
    for (const auto* key : {"items", "allOf", "anyOf", "oneOf"}) {
        if (!schema.HasMember(key)) continue;
        auto& child = schema[key];
        if (child.IsArray()) {
            for (auto& item : child.GetArray()) removeSchemaDefaults(item);
        } else {
            removeSchemaDefaults(child);
        }
    }
}
}  // namespace


namespace {
std::atomic<std::size_t> g_qwenXmlSchemaCompiles{0};

struct CompiledQwenXmlSchema : QwenXmlCompiledSchema {
    rapidjson::Document schemaValue;
    std::unique_ptr<rapidjson::SchemaDocument> compiled;

    bool validateArguments(const std::string& argumentsText) const override {
        if (argumentsText.find('\0') != std::string::npos) return false;
        rapidjson::Document args;
        args.Parse(argumentsText.c_str());
        if (args.HasParseError() || !args.IsObject() || !safeValidationInput(args, false))
            return false;
        rapidjson::SchemaValidator argumentsValidator(*compiled);
        return args.Accept(argumentsValidator);
    }
};

// Compile the same restricted Draft 4 schema used for executable output.
std::shared_ptr<CompiledQwenXmlSchema> compileOwnedQwenXmlToolSchema(const std::string& schemaText) {
    if (schemaText.empty() || schemaText.find('\0') != std::string::npos) return nullptr;
    auto compiled = std::make_shared<CompiledQwenXmlSchema>();
    compiled->schemaValue.Parse(schemaText.c_str());
    if (compiled->schemaValue.HasParseError() || !compiled->schemaValue.IsObject()) return nullptr;
    if (!safeValidationInput(compiled->schemaValue, false)) return nullptr;
    static const rapidjson::SchemaDocument metaSchema = []() {
        rapidjson::Document meta;
        meta.Parse(QWEN_DRAFT4_META_SCHEMA);
        auto& allocator = meta.GetAllocator();
        meta.AddMember("additionalProperties", false, allocator);
        // Empty required lists are common in native tool schemas, including
        // legitimate zero-parameter tools; treat them as no required fields.
        meta["definitions"]["stringArray"]["minItems"].SetInt(0);
        // Format assertions and newer dialect keywords are not silently ignored.
        meta["properties"].RemoveMember("format");
        // This RapidJSON version recursively compiles annotation/enum objects
        // as schemas too. Only scalar data can safely reach that compiler.
        rapidjson::Value scalar(rapidjson::kObjectType);
        rapidjson::Value scalarTypes(rapidjson::kArrayType);
        for (const auto* type : {"null", "boolean", "number", "string"})
            scalarTypes.PushBack(rapidjson::Value(type, allocator), allocator);
        scalar.AddMember("type", scalarTypes, allocator);
        meta["properties"]["default"].CopyFrom(scalar, allocator);
        meta["properties"]["enum"].AddMember("items", scalar, allocator);
        rapidjson::Value ref(rapidjson::kObjectType);
        ref.AddMember("type", "string", allocator);
        // Definitions are schema-valued and meta-validated. An arbitrary local
        // pointer could instead reach unchecked data or a schema-map container.
        // Restrict identifiers to exclude URI-decoded extra path segments.
        ref.AddMember("pattern", "^#/definitions/[A-Za-z0-9_.-]+$", allocator);
        meta["properties"].AddMember("$ref", ref, allocator);
        rapidjson::Value dialects(rapidjson::kArrayType);
        dialects.PushBack("http://json-schema.org/draft-04/schema#", allocator);
        dialects.PushBack("https://json-schema.org/draft-04/schema#", allocator);
        meta["properties"]["$schema"].AddMember("enum", dialects, allocator);
        return rapidjson::SchemaDocument(meta);
    }();
    rapidjson::SchemaValidator schemaValidator(metaSchema);
    if (!compiled->schemaValue.Accept(schemaValidator)) return nullptr;
    removeSchemaDefaults(compiled->schemaValue);
    if (!safeValidationInput(compiled->schemaValue, true)) return nullptr;
    g_qwenXmlSchemaCompiles.fetch_add(1, std::memory_order_relaxed);
    compiled->compiled = std::make_unique<rapidjson::SchemaDocument>(compiled->schemaValue);
    if (!compiled->compiled->IsSupportedSpecification() || !compiled->compiled->GetError().ObjectEmpty())
        return nullptr;
    return compiled;
}
}  // namespace

std::shared_ptr<const QwenXmlCompiledSchema> compileQwenXmlToolSchema(const std::string& schemaText) {
    return compileOwnedQwenXmlToolSchema(schemaText);
}

std::size_t qwenXmlToolSchemaCompileCount() {
    return g_qwenXmlSchemaCompiles.load(std::memory_order_relaxed);
}

bool isSupportedQwenXmlToolSchema(const std::string& schemaText) {
    return static_cast<bool>(compileQwenXmlToolSchema(schemaText));
}

bool validateQwenXmlToolArguments(const std::string& schemaText, const std::string& argumentsText) {
    const auto compiled = compileQwenXmlToolSchema(schemaText);
    return compiled && compiled->validateArguments(argumentsText);
}
}  // namespace ovms
