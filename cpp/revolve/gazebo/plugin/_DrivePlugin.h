#ifndef REVOLVE_DRIVE_PLUGIN_H
#define REVOLVE_DRIVE_PLUGIN_H



#include <gazebo/gazebo.hh>
#include <gazebo/physics/physics.hh>
#include <gazebo/common/common.hh>
#include <gazebo/msgs/msgs.hh>

#include <revolve/msgs/model_inserted.pb.h>

#include <boost/thread/mutex.hpp>

namespace revolve {
namespace gazebo {
	
class DrivePlugin : public ::gazebo::WorldPlugin {
public:

	// constructor
	DrivePlugin();
	
	virtual void Load(::gazebo::physics::WorldPtr _parent, sdf::ElementPtr _sdf);
	
protected:
	
	// handle request to add a sound source
	virtual void OnRequest(ConstRequestPtr & _msg);
	
	// update callback
	virtual void OnUpdate(const ::gazebo::common::UpdateInfo & _info);
	
	// world pointer
	::gazebo::physics::WorldPtr world_;

	// Transport node pointer
	::gazebo::transport::NodePtr node_;
	
	// Request subscriber
	::gazebo::transport::SubscriberPtr requestSub_;

	// Response publisher
	::gazebo::transport::PublisherPtr responsePub_;
	
	// Sound source pose publisher
	::gazebo::transport::PublisherPtr SoundSourcePosesPub_;
	
	// Pointer to the update event connection
	::gazebo::event::ConnectionPtr updateConnection_;
	
	// mutex for accessing soundSourceNames_ map
	boost::mutex sourceNamesMutex_;
	
	// map from sound source names to sound wavelengths
    std::map<std::string, double> soundSourceNames_;
	
	// frequency of sound source position publications
    double soundSourcesPosePubFreq_;
	
	// time of the latest publication:
    double lastPubTime_;
	
};
	
	
} // namespace gazebo
} // namespace revolve


#endif // REVOLVE_DRIVE_PLUGIN_H