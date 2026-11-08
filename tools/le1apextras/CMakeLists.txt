cmake_minimum_required (VERSION 3.27)
project (LE1APExtrasBuild LANGUAGES CXX)

# Builds LE1APExtras against the pinned vendor/LExASIs (LExSDKv2, spdlog, Common) without changing the submodule.
# The global options and ASI_TARGET follow LExASIs' own CMakeLists.txt, reduced to the LE1 target.

cmake_policy (SET CMP0057 NEW)
cmake_policy (SET CMP0077 NEW)

set (CMAKE_CXX_STANDARD 20)
set (CMAKE_CXX_STANDARD_REQUIRED ON)

set (LEXASIS_DIR "${CMAKE_CURRENT_SOURCE_DIR}/../../vendor/LExASIs")
cmake_path (NORMAL_PATH LEXASIS_DIR)

set (LEASI_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/out/$<CONFIG>)
set (CMAKE_LIBRARY_OUTPUT_DIRECTORY ${LEASI_OUTPUT_DIRECTORY})
set (CMAKE_ARCHIVE_OUTPUT_DIRECTORY ${LEASI_OUTPUT_DIRECTORY})
set (CMAKE_RUNTIME_OUTPUT_DIRECTORY ${LEASI_OUTPUT_DIRECTORY})

if (NOT (CMAKE_CXX_COMPILER_ID STREQUAL "MSVC" AND WIN32))
  message (FATAL_ERROR "!! LE1APExtras builds with MSVC on Windows only")
endif ()

add_compile_definitions ("_CRT_SECURE_NO_WARNINGS" "NOMINMAX")
add_compile_options ("/MP" "/utf-8" "/Zi"
  "$<$<IN_LIST:$<CONFIG>,DEBUG>:/MDd;/Od;/JMC>"
  "$<$<IN_LIST:$<CONFIG>,RELEASE>:/MD;/O1>"
)
add_link_options ("/DEBUG"
  "$<$<IN_LIST:$<CONFIG>,DEBUG>:/OPT:NOREF;/OPT:NOICF>"
  "$<$<IN_LIST:$<CONFIG>,RELEASE>:/OPT:REF;/OPT:ICF;/INCREMENTAL:NO>"
)

set (LEASI_COMPILE_DEFINITIONS "SPDLOG_ACTIVE_LEVEL=0" "$<$<IN_LIST:$<CONFIG>,DEBUG>:_DEBUG>")
set (LEASI_COMPILE_OPTIONS "/W4" "/WX" "/permissive" "/wd4121" "/wd4127" "/wd4702")

# ASI_TARGET (LE1 only): <name>-LE1, linked against <vlink>-LE1; SHARED targets are named LE1<name>.asi.
function (ASI_TARGET PROJ_TARGET PROJ_TYPE)
  cmake_parse_arguments (PROJ "" "" "GAMES;SOURCES;LINKS;VLINKS" ${ARGN})
  if (NOT "LE1" IN_LIST PROJ_GAMES)
    return ()
  endif ()
  list (TRANSFORM PROJ_SOURCES PREPEND "${CMAKE_CURRENT_SOURCE_DIR}/")
  set (LIBRARY_LINKS ${PROJ_LINKS})
  foreach (PROJ_VLINK IN LISTS PROJ_VLINKS)
    list (APPEND LIBRARY_LINKS "${PROJ_VLINK}-LE1")
  endforeach ()
  set (TARGET_NAME "${PROJ_TARGET}-LE1")
  add_library (${TARGET_NAME} ${PROJ_TYPE} ${PROJ_SOURCES})
  target_compile_definitions (${TARGET_NAME} PUBLIC ${LEASI_COMPILE_DEFINITIONS})
  target_compile_options (${TARGET_NAME} PUBLIC ${LEASI_COMPILE_OPTIONS})
  target_include_directories (${TARGET_NAME} PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/..)
  target_link_libraries (${TARGET_NAME} PUBLIC ${LIBRARY_LINKS})
  if (PROJ_TYPE STREQUAL "SHARED")
    set_target_properties (${TARGET_NAME} PROPERTIES OUTPUT_NAME "LE1${PROJ_TARGET}" SUFFIX ".asi")
  endif ()
endfunction ()

add_subdirectory ("${LEXASIS_DIR}/External" "${CMAKE_BINARY_DIR}/External")
add_subdirectory ("${LEXASIS_DIR}/Common" "${CMAKE_BINARY_DIR}/Common")
add_subdirectory ("LE1APExtras")
