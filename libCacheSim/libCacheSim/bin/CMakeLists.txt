


add_subdirectory(cachesim)
# add_subdirectory(traceWriter)
add_subdirectory(distUtil)
add_subdirectory(traceUtils)
add_subdirectory(traceAnalyzer)
add_subdirectory(SOSP23)


if (EXISTS ${CMAKE_CURRENT_SOURCE_DIR}/priv)
    message(STATUS "Found priv directory, building priv")
    add_subdirectory(priv)
endif()

