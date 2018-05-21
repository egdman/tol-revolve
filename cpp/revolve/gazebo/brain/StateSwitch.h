struct State
{
	std::string name;
	std::string nextName;
	double duration = 9999.0;
};



class StateSwitch
{
public:
	StateSwitch(std::vector<std::string> names, double currentTime)
	{
		numStates_ = names.size();
		lastTime_ = currentTime;
		for (int i = 0; i < numStates_; ++i) {
			stateName = names[i];
			nextName = names[(i+1) % numStates_]
			states_[stateName] = State {

			}
		}
	}
};