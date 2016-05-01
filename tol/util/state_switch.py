class State:
    def __init__(self, name, next_name):
        self.name = name
        self.next_name = next_name
        self.duration = 9999.0

    def set_duration(self, duration):
        self.duration = duration

    def get_duration(self):
        return self.duration

    def get_next_state_name(self):
        return self.next_name


class StateSwitch:
    def __init__(self, state_names, current_time):
        num_states = len(state_names)

        self.last_time = current_time
        self.states = {state_names[i]: State(name=state_names[i], next_name=state_names[(i+1)%num_states]) \
                       for i, name in enumerate(state_names)}
        self.current_state_name = state_names[0]

    def set_duration(self, state_name, duration):
        self.states[state_name].set_duration(duration)

    def get_duration(self, state_name):
        return self.states[state_name].get_duration()

    def get_current_state(self):
        return self.current_state_name

    def update(self, current_time):
        current_state = self.states[self.current_state_name]
        if current_time - self.last_time >= current_state.get_duration():

            self.current_state_name = current_state.get_next_state_name()
            self.last_time = current_time
        return self.current_state_name

    def switch_to_state(self, state_name, current_time):
        self.current_state_name = state_name
        self.last_time = current_time
