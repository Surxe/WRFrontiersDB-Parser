"""
Alternative Python DLL Injector using a simplified approach
"""
import ctypes
from ctypes import wintypes
import psutil
import os
from loguru import logger

# Windows constants
PROCESS_CREATE_THREAD = 0x0002
PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_VM_OPERATION = 0x0008
PROCESS_VM_WRITE = 0x0020
PROCESS_VM_READ = 0x0010
MEM_COMMIT = 0x1000
MEM_RESERVE = 0x2000
PAGE_READWRITE = 0x04
WAIT_OBJECT_0 = 0x00000000
INFINITE = 0xFFFFFFFF
MEM_RELEASE = 0x8000

class SimpleDLLInjector:
    def __init__(self):
        # Define function prototypes upfront
        self._setup_function_prototypes()
        
    def _setup_function_prototypes(self):
        # OpenProcess
        ctypes.windll.kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        ctypes.windll.kernel32.OpenProcess.restype = wintypes.HANDLE
        
        # VirtualAllocEx
        ctypes.windll.kernel32.VirtualAllocEx.argtypes = [
            wintypes.HANDLE, ctypes.c_void_p, ctypes.c_size_t, wintypes.DWORD, wintypes.DWORD
        ]
        ctypes.windll.kernel32.VirtualAllocEx.restype = ctypes.c_void_p
        
        # WriteProcessMemory
        ctypes.windll.kernel32.WriteProcessMemory.argtypes = [
            wintypes.HANDLE, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)
        ]
        ctypes.windll.kernel32.WriteProcessMemory.restype = wintypes.BOOL
        
        # GetModuleHandleW
        ctypes.windll.kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
        ctypes.windll.kernel32.GetModuleHandleW.restype = wintypes.HMODULE
        
        # GetProcAddress  
        ctypes.windll.kernel32.GetProcAddress.argtypes = [wintypes.HMODULE, wintypes.LPCSTR]
        ctypes.windll.kernel32.GetProcAddress.restype = ctypes.c_void_p
        
        # CreateRemoteThread
        ctypes.windll.kernel32.CreateRemoteThread.argtypes = [
            wintypes.HANDLE, ctypes.c_void_p, ctypes.c_size_t, ctypes.c_void_p, 
            ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)
        ]
        ctypes.windll.kernel32.CreateRemoteThread.restype = wintypes.HANDLE
        
        # WaitForSingleObject
        ctypes.windll.kernel32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        ctypes.windll.kernel32.WaitForSingleObject.restype = wintypes.DWORD
        
        # GetExitCodeThread
        ctypes.windll.kernel32.GetExitCodeThread.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
        ctypes.windll.kernel32.GetExitCodeThread.restype = wintypes.BOOL

    def get_process_id_by_name(self, process_name):
        """Get process ID by process name"""
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                if proc.info['name'].lower() == process_name.lower():
                    return proc.info['pid']
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        return None

    def inject_dll(self, process_name, dll_path):
        """Inject DLL into target process"""
        logger.info(f"Starting DLL injection: {dll_path} -> {process_name}")
        
        if not os.path.exists(dll_path):
            logger.error(f"DLL file not found: {dll_path}")
            return False
            
        process_id = self.get_process_id_by_name(process_name)
        if not process_id:
            logger.error(f"Process not found: {process_name}")
            return False
            
        logger.info(f"Target process PID: {process_id}")
        
        # Required access rights
        desired_access = (PROCESS_CREATE_THREAD | PROCESS_QUERY_INFORMATION | 
                         PROCESS_VM_OPERATION | PROCESS_VM_WRITE | PROCESS_VM_READ)
        
        # Open target process
        h_process = ctypes.windll.kernel32.OpenProcess(desired_access, False, process_id)
        if not h_process:
            error = ctypes.windll.kernel32.GetLastError()
            logger.error(f"Failed to open process {process_id}, error: {error}")
            return False
            
        logger.info(f"Process opened successfully, handle: {h_process}")
        
        try:
            # Prepare DLL path as string
            dll_path_bytes = dll_path.encode('utf-8') + b'\0'
            path_len = len(dll_path_bytes)
            
            # Allocate memory in target process
            remote_memory = ctypes.windll.kernel32.VirtualAllocEx(
                h_process, None, path_len, MEM_COMMIT | MEM_RESERVE, PAGE_READWRITE
            )
            
            if not remote_memory:
                error = ctypes.windll.kernel32.GetLastError()
                logger.error(f"VirtualAllocEx failed, error: {error}")
                return False
                
            logger.info(f"Allocated {path_len} bytes at: 0x{remote_memory:X}")
            
            # Write DLL path to remote process memory
            bytes_written = ctypes.c_size_t(0)
            if not ctypes.windll.kernel32.WriteProcessMemory(
                h_process, remote_memory, dll_path_bytes, path_len, ctypes.byref(bytes_written)
            ):
                error = ctypes.windll.kernel32.GetLastError()
                logger.error(f"WriteProcessMemory failed, error: {error}")
                ctypes.windll.kernel32.VirtualFreeEx(h_process, remote_memory, 0, MEM_RELEASE)
                return False
                
            logger.info(f"Wrote {bytes_written.value} bytes to remote process")
            
            # Get LoadLibraryA address
            h_kernel32 = ctypes.windll.kernel32.GetModuleHandleW("kernel32.dll")
            if not h_kernel32:
                error = ctypes.windll.kernel32.GetLastError()
                logger.error(f"GetModuleHandleW failed, error: {error}")
                ctypes.windll.kernel32.VirtualFreeEx(h_process, remote_memory, 0, MEM_RELEASE)
                return False
                
            load_library_addr = ctypes.windll.kernel32.GetProcAddress(h_kernel32, b"LoadLibraryA")
            if not load_library_addr:
                error = ctypes.windll.kernel32.GetLastError()
                logger.error(f"GetProcAddress failed, error: {error}")
                ctypes.windll.kernel32.VirtualFreeEx(h_process, remote_memory, 0, MEM_RELEASE)
                return False
                
            logger.info(f"LoadLibraryA address: 0x{load_library_addr:X}")
            
            # Create remote thread
            thread_id = wintypes.DWORD(0)
            h_thread = ctypes.windll.kernel32.CreateRemoteThread(
                h_process, None, 0, load_library_addr, remote_memory, 0, ctypes.byref(thread_id)
            )
            
            if not h_thread:
                error = ctypes.windll.kernel32.GetLastError()
                logger.error(f"CreateRemoteThread failed, error: {error}")
                ctypes.windll.kernel32.VirtualFreeEx(h_process, remote_memory, 0, MEM_RELEASE)
                return False
                
            logger.info(f"Remote thread created, ID: {thread_id.value}")
            
            # Wait for thread completion
            wait_result = ctypes.windll.kernel32.WaitForSingleObject(h_thread, INFINITE)
            if wait_result != WAIT_OBJECT_0:
                logger.error(f"Thread wait failed, result: {wait_result}")
                ctypes.windll.kernel32.CloseHandle(h_thread)
                ctypes.windll.kernel32.VirtualFreeEx(h_process, remote_memory, 0, MEM_RELEASE)
                return False
                
            # Get thread exit code
            exit_code = wintypes.DWORD(0)
            ctypes.windll.kernel32.GetExitCodeThread(h_thread, ctypes.byref(exit_code))
            
            # Clean up
            ctypes.windll.kernel32.CloseHandle(h_thread)
            ctypes.windll.kernel32.VirtualFreeEx(h_process, remote_memory, 0, MEM_RELEASE)
            
            if exit_code.value == 0:
                logger.error("LoadLibraryA returned NULL - injection failed")
                return False
            else:
                logger.info(f"DLL injection successful! Module handle: 0x{exit_code.value:X}")
                return True
                
        except Exception as e:
            logger.error(f"Exception during injection: {e}")
            return False
        finally:
            ctypes.windll.kernel32.CloseHandle(h_process)

def inject_dll_into_process(process_name, dll_path):
    """Convenience function for DLL injection"""
    injector = SimpleDLLInjector()
    return injector.inject_dll(process_name, dll_path)