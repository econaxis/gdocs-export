import sys, traceback

def show_thread_stacks():
    for thread_id, frame in sys._current_frames().items():
        print('\n--- Stack for thread {t} ---'.format(t=thread_id))
        traceback.print_stack(frame, file=sys.stdout)

show_thread_stacks()
