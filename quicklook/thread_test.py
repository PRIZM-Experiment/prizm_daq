import thread,time

def clock1(dt=0.5):
    while (True):
        print 'greetings from clock1'
        time.sleep(dt)
    return

def clock2(dt=0.8):
    while (True):
        print 'greetings from clock2'
        time.sleep(dt)

if __name__=='__main__':
    id1=thread.start_new_thread(clock1,())
    id2=thread.start_new_thread(clock2,())
    time.sleep(50)
