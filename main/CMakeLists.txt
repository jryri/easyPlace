ADD_EXECUTABLE(
    ePlace
    ePlace_main.cpp
    ${PROJECT_SOURCE_DIR}/Parser/parser.cpp
    ${PROJECT_SOURCE_DIR}/PlaceCommon/arghandler.cpp
    ${PROJECT_SOURCE_DIR}/PlaceCommon/objects.cpp
    ${PROJECT_SOURCE_DIR}/PlaceDB/placedb.cpp
    ${PROJECT_SOURCE_DIR}/Plot/plot.cpp
    ${PROJECT_SOURCE_DIR}/QPlace/qplace.cpp
    ${PROJECT_SOURCE_DIR}/FFT/fft.cpp
    ${PROJECT_SOURCE_DIR}/FFT/fftsg2d.cpp
    ${PROJECT_SOURCE_DIR}/FFT/fftsg.cpp
    ${PROJECT_SOURCE_DIR}/Optimization/nesterov.hpp
    ${PROJECT_SOURCE_DIR}/Optimization/opt.hpp
    ${PROJECT_SOURCE_DIR}/EPlace/eplace.cpp
    ${PROJECT_SOURCE_DIR}/Legalization/legalizer.cpp
    ${PROJECT_SOURCE_DIR}/DetailedPlacement/detailed.cpp
    ${PROJECT_SOURCE_DIR}/OpenroadInterface/interface.cpp

)
INCLUDE_DIRECTORIES (
	${PROJECT_SOURCE_DIR}/Parser
	${PROJECT_SOURCE_DIR}/PlaceCommon
	${PROJECT_SOURCE_DIR}/PlaceDB
    ${PROJECT_SOURCE_DIR}/Plot
    ${PROJECT_SOURCE_DIR}/Library/eigen-git-mirror
    ${PROJECT_SOURCE_DIR}/Library/CImg
    ${PROJECT_SOURCE_DIR}/QPlace
    ${PROJECT_SOURCE_DIR}/FFT
    ${PROJECT_SOURCE_DIR}/EPlace
    ${PROJECT_SOURCE_DIR}/Optimization
    ${PROJECT_SOURCE_DIR}/Legalization
    ${PROJECT_SOURCE_DIR}/DetailedPlacement
    ${PROJECT_SOURCE_DIR}/OpenroadInterface
    )

target_link_libraries(ePlace "-lgomp -lpthread -lm -ldl -lX11")