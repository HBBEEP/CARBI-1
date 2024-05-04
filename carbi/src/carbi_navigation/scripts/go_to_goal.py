#!/usr/bin/python3
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist, Pose
from std_msgs.msg import Float32MultiArray
import numpy as np
import tf2_ros
from tf2_ros import LookupException, ConnectivityException, ExtrapolationException
import tf_transformations

class CarbiGoToGoal(Node):
    def __init__(self):
        super().__init__('carbi_go_to_goal')

        self.tf_buffer = tf2_ros.Buffer()
        self.tf_listener = tf2_ros.TransformListener(self.tf_buffer, self)

        self.time_step = 0.01
        self.timer_ = self.create_timer(self.time_step, self.update)
        
        self.target_pos = [10.0, 10.0]
        self.pose = Pose()

        self.twist_publisher = self.create_publisher(Twist, '/cmd_vel', 10)
        self.set_target_subscription = self.create_subscription(Float32MultiArray, '/target_pos', self.set_target_pos, 10)


    def update(self):
        try:
            trans = self.tf_buffer.lookup_transform('base_footprint', 'base_link', rclpy.time.Time())
            pose = Pose()
            pose.position.x = trans.transform.translation.x
            pose.position.y = trans.transform.translation.y
            pose.position.z = trans.transform.translation.z
            pose.orientation = trans.transform.rotation
            self.pose = pose
            # print(f"x : {pose.position.x}, y : { pose.position.y }")
        except (LookupException, ConnectivityException, ExtrapolationException) as e:
            self.get_logger().error('Could not transform from base_link to map: %s' % str(e))
            return None

        msg = self.controller()
        self.twist_publisher.publish(msg)


    def controller(self):
        msg = Twist()

        current_pos = np.array([self.pose.position.x, self.pose.position.y])
        dp = self.target_pos - current_pos
        _, _, theta = tf_transformations.euler_from_quaternion([self.pose.orientation.x,
                                                        self.pose.orientation.y,
                                                        self.pose.orientation.z,
                                                        self.pose.orientation.w])
        e = np.arctan2(dp[1], dp[0]) - theta
        K = 0.50
        w = K * np.arctan2(np.sin(e), np.cos(e))

        vx = dp[0] if dp[0] < 2.0 else 2.0
        vy = dp[1] if dp[1] < 2.0 else 2.0

        if np.linalg.norm(dp) < 0.3:
            vx = 0.0
            vy = 0.0
            w = 0.0

        msg.linear.x = vx
        msg.linear.y = vy
        msg.angular.z = w
        return msg

    def set_target_pos(self, msg):
        self.target_pos = msg.data

def main(args=None):
    rclpy.init(args=args)
    node = CarbiGoToGoal()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__=='__main__':
    main()