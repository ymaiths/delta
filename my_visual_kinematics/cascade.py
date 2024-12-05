import numpy as np
import matplotlib.pyplot as plt

# Robot Parameters
f = 0.3    # Base equilateral triangle side length
e = 0.1    # End effector equilateral triangle side length
rf = 0.5   # Upper arm length
re = 0.5   # Lower arm length
tan30 = 1 / np.sqrt(3)

# P-controller constants
Kp_pos = 10  # Proportional gain for position
Kp_vel = 5   # Proportional gain for velocity

# Gravity compensation parameters
mass = 0.5  # Mass at end-effector (kg)
g = 9.81    # Gravitational acceleration (m/s^2)

# Maximum velocity and acceleration for trapezoidal profile
v_max = 0.1  # Max velocity (m/s)
a_max = 0.2  # Max acceleration (m/s^2)

# Function for Trapezoidal Velocity Profile
def generate_trapezoidal_trajectory(start, end, v_max, a_max, duration=0.25):
    distance = np.linalg.norm(end - start)
    t_acc = v_max / a_max  # Time to reach max velocity
    distance_acc = 0.5 * a_max * t_acc**2
    if distance_acc * 2 > distance:
        t_acc = np.sqrt(distance / a_max)
        v_max = a_max * t_acc
        distance_acc = 0.5 * a_max * t_acc**2
    t_total = 2 * t_acc
    t = np.linspace(0, duration, 100)
    trajectory = np.linspace(start, end, len(t))
    return t, trajectory

# Function for Inverse Kinematics
def inverse_kinematics_with_velocity(x, y, z, vx, vy, vz):
    def calculate_angle(x0, y0, z0):
        y1 = -0.5 * f * tan30
        y0 -= 0.5 * e * tan30
        a = (x0**2 + y0**2 + z0**2 + rf**2 - re**2 - y1**2) / (2 * z0)
        b = (y1 - y0) / z0
        d = -(a + b * y1)**2 + rf * (b**2 * rf + rf)
        if d < 0:
            raise ValueError("Target position is not reachable.")
        yj = (y1 - a * b - np.sqrt(d)) / (b**2 + 1)
        zj = a + b * yj
        theta = np.arctan(-zj / (y1 - yj))
        return np.degrees(theta)

    theta1 = calculate_angle(x, y, z)
    cos120, sin120 = np.cos(2 * np.pi / 3), np.sin(2 * np.pi / 3)
    cos240, sin240 = np.cos(4 * np.pi / 3), np.sin(4 * np.pi / 3)
    x_prime, y_prime = x * cos120 + y * sin120, y * cos120 - x * sin120
    x_double_prime, y_double_prime = x * cos240 + y * sin240, y * cos240 - x * sin240
    theta2 = calculate_angle(x_prime, y_prime, z)
    theta3 = calculate_angle(x_double_prime, y_double_prime, z)
    J = jacobian(theta1, theta2, theta3)
    cartesian_velocity = np.array([vx, vy, vz])
    joint_velocity = np.linalg.pinv(J).dot(cartesian_velocity)
    return (theta1, theta2, theta3), joint_velocity

# Jacobian matrix for Delta robot
def jacobian(theta1, theta2, theta3):
    J = np.array([
        [-rf * np.sin(np.radians(theta1)), -rf * np.sin(np.radians(theta2)), -rf * np.sin(np.radians(theta3))],
        [rf * np.cos(np.radians(theta1)), rf * np.cos(np.radians(theta2)), rf * np.cos(np.radians(theta3))],
        [0, 0, 0]
    ])
    return J

# Position Controller
def position_control(current_pos, target_pos):
    error = target_pos - current_pos
    v_desired = Kp_pos * error
    return v_desired

# Velocity Controller
def velocity_control(v_desired, v_current):
    error = v_desired - v_current
    torque = Kp_vel * error
    return torque

# Simulating the cascade control system
def simulate_cascade_control(start_position, target_position):
    # target_position = np.array([0.3, 0.2, -0.5])
    # start_position = np.array([0.0, 0.0, 0.0])
    t, trajectory = generate_trapezoidal_trajectory(start_position, target_position, v_max, a_max)
    current_position = start_position.copy()
    current_velocity = np.array([0.0, 0.0, 0.0])
    joint_angles, joint_velocities, torques = [], [], []

    for i in range(len(t)):  # Start from index 0
        if i > 0:
            v_cartesian = (trajectory[i] - trajectory[i - 1]) / (t[i] - t[i - 1])
        else:
            v_cartesian = np.array([0.0, 0.0, 0.0])  # Assume zero velocity at the start

        try:
            (theta1, theta2, theta3), joint_velocity = inverse_kinematics_with_velocity(
                trajectory[i][0], trajectory[i][1], trajectory[i][2], v_cartesian[0], v_cartesian[1], v_cartesian[2]
            )
        except ValueError:
            print(f"Target position at step {i} is not reachable.")
            joint_velocity = np.array([0.0, 0.0, 0.0])  # Handle unreachable positions
            theta1, theta2, theta3 = 0.0, 0.0, 0.0
        
        v = np.sqrt(v_cartesian[0]**2 + v_cartesian[1]**2 + v_cartesian[2]**2)
        joint_angles.append([theta1, theta2, theta3])
        joint_velocities.append(joint_velocity)

        if i > 0:
            v_desired = position_control(current_position, trajectory[i])
            torque = velocity_control(v_desired, current_velocity)
        else:
            v_desired = np.array([0.0, 0.0, 0.0])
            torque = np.array([0.0, 0.0, 0.0])

        torques.append(torque)
        current_velocity += torque * (t[i] - t[i - 1]) if i > 0 else np.array([0.0, 0.0, 0.0])
        current_position += current_velocity * (t[i] - t[i - 1]) if i > 0 else np.array([0.0, 0.0, 0.0])

    return joint_angles, joint_velocities, torques, t, v

# Run the simulation
joint_angles, joint_velocities, torques, t, v = simulate_cascade_control()

# Plot results
# plt.figure(figsize=(12, 9))
# plt.subplot(3, 1, 1)
# plt.plot(t, np.array(joint_angles)[:, 0], label='Theta1')
# plt.plot(t, np.array(joint_angles)[:, 1], label='Theta2')
# plt.plot(t, np.array(joint_angles)[:, 2], label='Theta3')
# plt.title('Joint Angles')
# plt.legend()
# plt.subplot(3, 1, 2)
# plt.plot(t, np.array(joint_velocities)[:, 0], label='Joint Velocity 1')
# plt.legend()
# plt.subplot(3, 1, 3)
# plt.plot(t, np.array(torques)[:, 0], label='Torque 1')
# plt.legend()
# plt.show()