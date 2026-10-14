"""Small Python 3.7 binding for the shipped Prism 0.18.2 C ABI.

Prism owns screen-reader detection and communication. Windows fallback speech
stays in the speech module so existing fallback voice settings still apply.
"""
import ctypes
import threading
import time
import queue


class _Result:
    # The game's stripped standard library does not ship concurrent.futures.
    def __init__(self):
        self.done = threading.Event()
        self.value = None
        self.error = None
    def set_result(self, value):
        self.value = value
        self.done.set()
    def set_exception(self, error):
        self.error = error
        self.done.set()
    def result(self):
        self.done.wait()
        if self.error is not None:
            raise self.error
        return self.value


class _NativeReader:
    def __init__(self, path, log):
        self.log = log
        self.lock = threading.RLock()
        self.dll = ctypes.CDLL(path)
        self.backend = None
        self.name = None
        self.next_probe = 0.0
        p = ctypes.c_void_p
        u = ctypes.c_uint64
        signatures = {
            'prism_init': ([p], p),
            'prism_registry_count': ([p], ctypes.c_size_t),
            'prism_registry_id_at': ([p, ctypes.c_size_t], u),
            'prism_registry_name': ([p, u], ctypes.c_char_p),
            'prism_registry_create': ([p, u], p),
            'prism_backend_initialize': ([p], ctypes.c_int),
            'prism_backend_get_features': ([p], u),
            'prism_backend_free': ([p], None),
            'prism_backend_speak': ([p, ctypes.c_char_p, ctypes.c_bool], ctypes.c_int),
            'prism_backend_braille': ([p, ctypes.c_char_p], ctypes.c_int),
            'prism_backend_stop': ([p], ctypes.c_int),
        }
        for name, (args, result) in signatures.items():
            fn = getattr(self.dll, name)
            fn.argtypes, fn.restype = args, result
        self.context = self.dll.prism_init(None)
        if not self.context:
            raise RuntimeError('Prism context initialization failed')
        self.ids = []
        for i in range(self.dll.prism_registry_count(self.context)):
            ident = self.dll.prism_registry_id_at(self.context, i)
            name = (self.dll.prism_registry_name(self.context, ident) or b'').decode('utf-8', 'replace')
            # UIA can report success without a reader actually speaking.
            if name.lower().replace(' ', '') not in ('sapi', 'onecore', 'uia'):
                self.ids.append((ident, name))
        self.select()

    def select(self, force=False):
        with self.lock:
            if force:
                self._drop()
            if self.backend:
                return True
            if not force and time.monotonic() < self.next_probe:
                return False
            self.next_probe = time.monotonic() + 2.0
            for ident, name in self.ids:
                backend = self.dll.prism_registry_create(self.context, ident)
                if not backend:
                    continue
                if self.dll.prism_backend_initialize(backend) == 0:
                    self.backend, self.name = backend, name
                    self.log('Prism screen reader: ' + name)
                    return True
                self.dll.prism_backend_free(backend)
            return False

    def _drop(self):
        if self.backend:
            self.dll.prism_backend_free(self.backend)
        self.backend, self.name = None, None

    def has_braille(self):
        with self.lock:
            return bool(self.backend and
                        self.dll.prism_backend_get_features(self.backend) & 16)

    def output(self, text, brief, mode, interrupt):
        with self.lock:
            if not self.select():
                return False
            if mode == 'only':
                result = self.dll.prism_backend_braille(
                    self.backend, brief.encode('utf-8'))
                if result:
                    self.log('Prism braille failed: {}'.format(result))
                return True  # Never substitute audio for braille-only output.
            result = self.dll.prism_backend_speak(
                self.backend, text.encode('utf-8'), interrupt)
            if result:
                self.log('Prism speech failed: {} ({})'.format(self.name, result))
                self._drop()
                return False
            if mode != 'off' and self.has_braille():
                self.dll.prism_backend_braille(
                    self.backend, (text if mode == 'full' else brief).encode('utf-8'))
            return True

    def stop(self):
        with self.lock:
            return bool(self.backend and
                        self.dll.prism_backend_stop(self.backend) == 0)


class Reader:
    """Own every native call on one thread, including COM initialization.

Speech may arrive from the simulation thread or a deferred speech timer.
COM readers must never be created on one of these and called on another.
"""
    def __init__(self, path, log):
        self.jobs = queue.Queue()
        self.ready = _Result()
        self.thread = threading.Thread(target=self._run, args=(path, log), daemon=True)
        self.thread.start()
        self.ready.result()

    def _run(self, path, log):
        try:
            native = _NativeReader(path, log)
        except Exception as ex:
            self.ready.set_exception(ex)
            return
        self.ready.set_result(True)
        while True:
            method, args, kwargs, result = self.jobs.get()
            try:
                value = native.name if method == 'name' else getattr(native, method)(*args, **kwargs)
                result.set_result(value)
            except Exception as ex:
                result.set_exception(ex)

    def _call(self, method, *args, **kwargs):
        result = _Result()
        self.jobs.put((method, args, kwargs, result))
        return result.result()

    @property
    def name(self): return self._call('name')
    def select(self, force=False): return self._call('select', force=force)
    def has_braille(self): return self._call('has_braille')
    def output(self, text, brief, mode, interrupt):
        return self._call('output', text, brief, mode, interrupt)
    def stop(self): return self._call('stop')
