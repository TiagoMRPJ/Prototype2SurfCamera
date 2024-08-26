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
        
  speed = 3
  sleeptime = 5
  io.setPanGoalVelocity(-speed)
  time.sleep(sleeptime)
  io.setPanGoalVelocity(speed)
  time.sleep(sleeptime)
  io.setPanGoalVelocity(0)

if __name__ == "__main__":
    io = IOBoardDriver.FrontBoardDriver()
    z = Zoom.SoarCameraZoomFocus()
    z.set_zoom_position(1)
    time.sleep(2)
    for i in range(20):
      z.set_zoom_position(1 + 0.1*i)
      time.sleep(0.3)
    
