## Chapter 10
# subprocess 
    # Provides an API for creating and communicating with secondary processes.
    # It is especially good at running programs that produce or consume text, since the API supports passing data pack and forth through the stdin/stdout channels of the new process
# signal
    # Exposes the UNIX signal mechanism for sending events to other processes.  
    # The signals are processed asynchronously, usually by interrupting what the program is doing when the signal arrives.  
    # Signalling is useful as a coarse messaging system, but other inter-process communication techniques are more reliable and deliver more complicated messages
# threading
    # Includes a high-level, OOAPI for working with concurrency from Python
    # Thread objects run concurrently within the same process and share memory
    # Using threads is an easy way to scale for tasks that are more I/O bound than CPU bound
# multiprocessing
    # Mirrors threading, except that instead of a THread class it provides a Process.
    # Each Process is a true system process without shared memory, but multiprocessing provides featured for sharing data and parsing messages between them
    # In many cases, converting from threads to processes is as simple as changing a few import statements