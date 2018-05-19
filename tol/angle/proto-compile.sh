GAZEBO_INCLUDE_DIR=/usr/local/include/gazebo-6.5

protoc -I ${GAZEBO_INCLUDE_DIR} -I ${GAZEBO_INCLUDE_DIR}/gazebo/msgs/proto -I spec --python_out=spec/ spec/msgs/*.proto
