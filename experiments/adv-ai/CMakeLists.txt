set(directorAI_SRCS
		CDirectorAI.cpp
)

set(directorAI_HEADERS
		StdInc.h

		CDirectorAI.h
)

assign_source_group(${directorAI_SRCS} ${directorAI_HEADERS})

add_library(DirectorAI OBJECT ${directorAI_SRCS} ${directorAI_HEADERS})
target_compile_definitions(DirectorAI PRIVATE VCMI_DLL=1)

target_include_directories(DirectorAI PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})
target_link_libraries(DirectorAI PRIVATE vcmiMain)

vcmi_set_output_dir(DirectorAI "AI")
enable_pch(DirectorAI)
