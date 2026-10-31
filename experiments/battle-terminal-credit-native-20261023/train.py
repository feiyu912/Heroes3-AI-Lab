"""Lightweight spawn-safe bootstrap: workers must not import Torch/learner code."""
if __name__=='__main__':
    import signal
    from leases import verify_pair
    verify_pair()
    def stop(signum,frame):raise KeyboardInterrupt('Controller stopped owned learner session')
    signal.signal(signal.SIGTERM,stop)
    signal.signal(signal.SIGINT,stop)
    from learner_impl import main
    main()
