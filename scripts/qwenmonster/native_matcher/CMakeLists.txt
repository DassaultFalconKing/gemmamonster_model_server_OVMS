cmake_minimum_required(VERSION 3.20)
project(qwenmonster_xml_matcher_probe LANGUAGES CXX)
set(CMAKE_CXX_STANDARD 17)
set(XGRAMMAR_SOURCE_DIR "" CACHE PATH "Exact locked XGrammar source")
set(XGRAMMAR_LIBRARY "" CACHE FILEPATH "Static library built from that source")
set(OPENVINO_RUNTIME_DIR "" CACHE PATH "Matching installed OpenVINO/GenAI runtime")
foreach(input XGRAMMAR_SOURCE_DIR XGRAMMAR_LIBRARY OPENVINO_RUNTIME_DIR)
    if(NOT EXISTS "${${input}}")
        message(FATAL_ERROR "Explicit existing ${input} is required; no upstream fallback")
    endif()
endforeach()
add_executable(qwenmonster_xml_matcher_probe probe.cpp)
target_include_directories(qwenmonster_xml_matcher_probe PRIVATE
    "${OPENVINO_RUNTIME_DIR}/include"
    "${XGRAMMAR_SOURCE_DIR}/include"
    "${XGRAMMAR_SOURCE_DIR}/3rdparty/dlpack/include")
if(WIN32)
    target_link_libraries(qwenmonster_xml_matcher_probe PRIVATE
        "${XGRAMMAR_LIBRARY}"
        "${OPENVINO_RUNTIME_DIR}/lib/intel64/Release/openvino_genai.lib")
else()
    message(FATAL_ERROR "This probe currently has a Windows linkage recipe only")
endif()
