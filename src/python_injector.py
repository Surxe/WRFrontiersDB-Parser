"""
Python DLL Injector using Windows API
Replaces the need for external DLL injector executable
"""
import ctypes
from ctypes import wintypes
import psutil
import os
from loguru import logger

# Windows API constants
PROCESS_ALL_ACCESS = 0x1F0FFF
MEM_COMMIT = 0x1000
MEM_RESERVE = 0x2000
PAGE_READWRITE = 0x04
WAIT_OBJECT_0 = 0x00000000
INFINITE = 0xFFFFFFFF

# Windows API functions
kernel32 = ctypes.windll.kernel32
advapi32 = ctypes.windll.advapi32

class DLLInjector:
    def __init__(self):
        self.kernel32 = kernel32
        
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
        """
        Inject a DLL into a target process
        
        Args:
            process_name (str): Name of the target process (e.g., "game.exe")
            dll_path (str): Full path to the DLL file to inject
            
        Returns:
            bool: True if injection was successful, False otherwise
        """
        logger.info(f"Starting DLL injection: {dll_path} -> {process_name}")
        
        # Validate DLL file exists
        if not os.path.exists(dll_path):
            logger.error(f"DLL file not found: {dll_path}")
            return False
            
        # Get process ID
        process_id = self.get_process_id_by_name(process_name)
        if not process_id:
            logger.error(f"Process not found: {process_name}")
            return False
            
        logger.info(f"Found target process {process_name} with PID: {process_id}")
        
        try:
            # Open the target process
            process_handle = self.kernel32.OpenProcess(
                PROCESS_ALL_ACCESS,
                False,
                process_id
            )
            
            if not process_handle:
                error_code = self.kernel32.GetLastError()
                logger.error(f"Failed to open process {process_id}. Error code: {error_code}")
                return False
                
            logger.info(f"Successfully opened process handle: {process_handle}")
            
            # Convert DLL path to bytes
            dll_path_bytes = dll_path.encode('utf-8') + b'\0'
            dll_path_size = len(dll_path_bytes)
            
            # Allocate memory in target process
            allocated_memory = self.kernel32.VirtualAllocEx(
                process_handle,
                None,
                dll_path_size,
                MEM_COMMIT | MEM_RESERVE,
                PAGE_READWRITE
            )
            
            if not allocated_memory:
                error_code = self.kernel32.GetLastError()
                logger.error(f"Failed to allocate memory in target process. Error code: {error_code}")
                self.kernel32.CloseHandle(process_handle)
                return False
                
            logger.info(f"Allocated memory at address: 0x{allocated_memory:X}")
            
            # Write DLL path to allocated memory
            bytes_written = wintypes.DWORD(0)
            write_result = self.kernel32.WriteProcessMemory(
                process_handle,
                allocated_memory,
                dll_path_bytes,
                dll_path_size,
                ctypes.byref(bytes_written)
            )
            
            if not write_result:
                error_code = self.kernel32.GetLastError()
                logger.error(f"Failed to write to process memory. Error code: {error_code}")
                self.kernel32.VirtualFreeEx(process_handle, allocated_memory, 0, 0x8000)
                self.kernel32.CloseHandle(process_handle)
                return False
                
            logger.info(f"Written {bytes_written.value} bytes to process memory")
            
            # Get LoadLibraryA function address
            loadlibrary_addr = self.kernel32.GetProcAddress(
                self.kernel32.GetModuleHandleW("kernel32.dll"),
                b"LoadLibraryA"
            )
            
            if not loadlibrary_addr:
                logger.error("Failed to get LoadLibraryA address")
                self.kernel32.VirtualFreeEx(process_handle, allocated_memory, 0, 0x8000)
                self.kernel32.CloseHandle(process_handle)
                return False
                
            logger.info(f"LoadLibraryA address: 0x{loadlibrary_addr:X}")
            
            # Create remote thread to execute LoadLibraryA
            thread_id = wintypes.DWORD(0)
            thread_handle = self.kernel32.CreateRemoteThread(
                process_handle,
                None,
                0,
                loadlibrary_addr,
                allocated_memory,
                0,
                ctypes.byref(thread_id)
            )
            
            if not thread_handle:
                error_code = self.kernel32.GetLastError()
                logger.error(f"Failed to create remote thread. Error code: {error_code}")
                self.kernel32.VirtualFreeEx(process_handle, allocated_memory, 0, 0x8000)
                self.kernel32.CloseHandle(process_handle)
                return False
                
            logger.info(f"Created remote thread with ID: {thread_id.value}")
            
            # Wait for the thread to complete
            wait_result = self.kernel32.WaitForSingleObject(thread_handle, INFINITE)
            
            if wait_result == WAIT_OBJECT_0:
                # Get thread exit code (which is the return value of LoadLibraryA)
                exit_code = wintypes.DWORD(0)
                self.kernel32.GetExitCodeThread(thread_handle, ctypes.byref(exit_code))
                
                if exit_code.value != 0:
                    logger.info(f"DLL injection successful! LoadLibraryA returned: 0x{exit_code.value:X}")
                    success = True
                else:
                    logger.error("DLL injection failed - LoadLibraryA returned 0")
                    success = False
            else:
                logger.error(f"Thread wait failed with result: {wait_result}")
                success = False
            
            # Cleanup
            self.kernel32.CloseHandle(thread_handle)
            self.kernel32.VirtualFreeEx(process_handle, allocated_memory, 0, 0x8000)
            self.kernel32.CloseHandle(process_handle)
            
            return success
            
        except Exception as e:
            logger.error(f"Exception during DLL injection: {str(e)}")
            return False

def inject_dll_into_process(process_name, dll_path):
    """
    Convenience function to inject DLL into a process
    
    Args:
        process_name (str): Name of the target process
        dll_path (str): Full path to the DLL file
        
    Returns:
        bool: True if injection was successful
    """
    injector = DLLInjector()
    return injector.inject_dll(process_name, dll_path)