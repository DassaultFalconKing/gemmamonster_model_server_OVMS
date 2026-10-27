// Copyright 2026 Intel Corporation. SPDX-License-Identifier: Apache-2.0
#include <gtest/gtest.h>
#include <string>
#include "src/llm/io_processing/lfm2/thought_demotion.hpp"

using ovms::lfm2::shouldDemoteSegment;

TEST(LfmThoughtDemotionReview, WellFormedAndMalformedPlans) {
    EXPECT_TRUE(shouldDemoteSegment(R"({"explanation":"need cwd","plan":[1],"commands":["bash /workspace"]})"));
    EXPECT_TRUE(shouldDemoteSegment(R"({"explanation":"draft","plan":[unterminated})"));
    EXPECT_FALSE(shouldDemoteSegment(R"(Before running commands: {"plan":[]})"));
    EXPECT_TRUE(shouldDemoteSegment(R"({'steps': ['one']})"));
}

TEST(LfmThoughtDemotionReview, PseudoToolLinesRequireWholeSegment) {
    EXPECT_TRUE(shouldDemoteSegment("[tool:cwd] /home/user\n[tool:write] x"));
    EXPECT_FALSE(shouldDemoteSegment("[tool:]"));
    EXPECT_FALSE(shouldDemoteSegment("A real response:\n[tool:cwd] /home/user"));
    EXPECT_FALSE(shouldDemoteSegment("Type [tool:cwd] in your documentation."));
}

TEST(LfmThoughtDemotionReview, KeyPositionsNotNestedOrValues) {
    EXPECT_FALSE(shouldDemoteSegment(R"({"info":{"plan":"do not classify nested"}})"));
    EXPECT_FALSE(shouldDemoteSegment(R"({"description":"\"plan\": \"looks like a key\""})"));
    EXPECT_FALSE(shouldDemoteSegment("The plan and explanation are below."));
    EXPECT_FALSE(shouldDemoteSegment(R"({"message":"not a plan"})"));
    EXPECT_FALSE(shouldDemoteSegment(" "));
}

TEST(LfmThoughtDemotionReview, LeadingProseIsAlwaysVisible) {
    EXPECT_FALSE(shouldDemoteSegment(std::string(1, 'x') + R"({"plan":[]})"));
    EXPECT_FALSE(shouldDemoteSegment(std::string(200, 'x') + R"({"plan":[]})"));
    EXPECT_FALSE(shouldDemoteSegment(std::string(201, 'x') + R"({"plan":[]})"));
}

TEST(LfmThoughtDemotionReview, NoUnclosedObjectOrTruncatedMarkerPromotion) {
    EXPECT_FALSE(shouldDemoteSegment(R"({"plan":[1,2)"));
    EXPECT_FALSE(shouldDemoteSegment("[tool:"));
    EXPECT_FALSE(shouldDemoteSegment("A perfectly normal assistant reply."));
}
