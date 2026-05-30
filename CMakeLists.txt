cmake_minimum_required(VERSION 3.8)
project(photo_pupper)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

find_package(ament_cmake REQUIRED)
find_package(rosidl_default_generators REQUIRED)

# Generate custom service interface
rosidl_generate_interfaces(${PROJECT_NAME}
  "srv/PrintImage.srv"
  "srv/ProcessPhoto.srv"
)

install(DIRECTORY photo_pupper
  DESTINATION lib/python3.10/site-packages
)

install(PROGRAMS
  photo_pupper/fsm_node.py
  photo_pupper/movement_node.py
  photo_pupper/people_detection_node.py
  photo_pupper/photo_processing_node.py
  photo_pupper/printer_node.py
  photo_pupper/screen_node.py
  photo_pupper/touch_node.py
  DESTINATION lib/${PROJECT_NAME}
)

install(DIRECTORY launch config resource
  DESTINATION share/${PROJECT_NAME}
)

ament_package()
