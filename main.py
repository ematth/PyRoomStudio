
from render import Render
from acoustic import Acoustic
import sys
import time

class App():
    def __init__(self, model_name):
        self.name = 'App'
        self.model = None
        self.render = Render(filename=model_name)
        self.acoustic = Acoustic()

    def run(self):

        while True:
            # Main loop
            self.render.taskMgr.step()
            #time.sleep(0.025) # crude 30FPS cap, switch to Panda3D's clock later
            self.acoustic.simulate()
            # if keyboard.is_pressed('q'):
            #     sys.exit()
            if self.render.win.isClosed():
                sys.exit()


if __name__ == '__main__':
    model_name: str = 'resources/cottage_obj.obj' if (len(sys.argv) < 2) else sys.argv[1]
    app = App(model_name)
    app.run()
