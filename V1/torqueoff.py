import IOBoardDriver
import Zoom
import time


def testTilt(io):
  io.setAngles(pan=0, tilt=0)
  time.sleep(4)
  for i in range(30):
      io.setAngles(pan=0, tilt=0.5*i)
      time.sleep(1)
  io.setAngles(pan=0, tilt=0)
  

def testPan(io):
  io.setPanVelocityControl()
        
  speed = 5
  sleeptime = 1000
  io.setPanGoalVelocity(speed)
  time.sleep(sleeptime)
  #io.setPanGoalVelocity(-speed)
  #time.sleep(sleeptime)
  io.setPanGoalVelocity(0)

if __name__ == "__main__":
    io = IOBoardDriver.FrontBoardDriver()
    io.setPanPositionControl()
    io.setAngles(pan = -10, tilt = 0)
    