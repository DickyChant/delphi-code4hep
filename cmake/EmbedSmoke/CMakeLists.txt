cmake_minimum_required(VERSION 3.24)
project(delphi_code4hep_embed_smoke LANGUAGES CXX)

set(DELPHI_EDM4HEP_SOURCE_DIR "" CACHE PATH
    "Path to delphi-edm4hep's inner CMake source directory")
if(NOT EXISTS "${DELPHI_EDM4HEP_SOURCE_DIR}/CMakeLists.txt")
  message(FATAL_ERROR
    "DELPHI_EDM4HEP_SOURCE_DIR must contain the converter CMakeLists.txt")
endif()

enable_testing()
add_subdirectory("${DELPHI_EDM4HEP_SOURCE_DIR}" delphi_edm4hep)
