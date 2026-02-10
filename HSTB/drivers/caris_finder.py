import os
from winreg import ConnectRegistry, HKEY_LOCAL_MACHINE, OpenKey, QueryValueEx

HIPS_NAME = "HIPS"
HIPS_VERSIONS = ('12.1', '12.0', '11.4', '11.3', '11.2', '11.1', '10.4', '10.3', '10.2')
BASE_EDITOR_NAME = "BASE Editor"
BASE_EDITOR_VERSIONS = ('6.1', '5.5', '5.4', '5.3', '5.2', '5.1', '4.4', '4.3', '4.2')

def caris_command_finder(exe_name, accepted_versions, app_key, get_all_versions=False, subdir='bin'):
    """
        Searches for a specific CARIS executable within the system registry and retrieves the executable path
        for the first valid version or all accepted versions.

        Parameters:
        -----------
        exe_name : str
            The name of the CARIS executable to search for (e.g., 'carisbatch.exe').
        accepted_versions : list of str
            A list of accepted CARIS versions to search for, specified as version strings (e.g., ['10.0', '11.0']).
        app_key : str
            The application key under the CARIS registry path to search for (e.g., 'HIPS and SIPS').
        get_all_versions : bool, optional
            If True, returns paths for all accepted versions found (default is False).

        Returns:
        --------
        tuple or list
            If get_all_versions is False (default):
                - Returns a tuple containing:
                    - batch_engine : str
                        The full path to the specified CARIS executable for the first valid version found.
                    - vers : float
                        The version number as a float of the first valid version found.
            If get_all_versions is True:
                - Returns a list of tuples:
                    - Each tuple contains:
                        - batch_engine : str
                            The full path to the specified CARIS executable.
                        - vers : float
                            The version number as a float for each valid version found.

        Raises:
        -------
        WindowsError
            If an error occurs while accessing the Windows registry.

        Notes:
        ------
        - This function requires access to the Windows registry and will only work on Windows systems.
        - If no valid CARIS executable is found for any of the provided versions, the returned path will be empty.

        Example:
        --------
        >>> caris_command_finder('carisbatch.exe', ['10.0', '11.0'], 'HIPS and SIPS')
        ('C:\\Program Files\\CARIS\\HIPS and SIPS 10.0\\bin\\carisbatch.exe', 10.0)

        >>> caris_command_finder('carisbatch.exe', ['10.0', '11.0'], 'HIPS and SIPS', get_all_versions=True)
        [['C:\\Program Files\\CARIS\\HIPS and SIPS 10.0\\bin\\carisbatch.exe', 10.0],
        ['C:\\Program Files\\CARIS\\HIPS and SIPS 11.0\\bin\\carisbatch.exe', 11.0]]
        """
    versions = []
    regHKLM = ConnectRegistry(None, HKEY_LOCAL_MACHINE)
    for vHIPS in accepted_versions:
        try:
            kBDB = OpenKey(regHKLM, os.sep.join(('SOFTWARE', 'CARIS', app_key, vHIPS, 'Environment Variables')))
            p2hipsinst = QueryValueEx(kBDB, "install_dir")[0]
            batch_engine = os.path.join(p2hipsinst, subdir, exe_name)
            # if the carisbatch doesn't exist then continue to the next version of caris
            if not os.path.exists(batch_engine):
                continue
            vers = float(vHIPS)
            versions.append([batch_engine, vers])
            if not get_all_versions:
                break
        except WindowsError:
            continue

    if get_all_versions:
        return versions
    else:
        return versions[0] if versions else ('', '')


def get_hips_command_from_version(vers):
    """
           Retrieves the CARIS HIPS batch engine path for a specified version.

           Parameters:
           -----------
           vers : float or str
               The version number of CARIS HIPS and SIPS to search for (e.g., 11.4 or '11.4').

           Returns:
           --------
           str
               The full path to the `carisbatch.exe` executable for the specified CARIS HIPS version.

           Raises:
           -------
           Exception
               If the batch engine for the specified CARIS HIPS version is not found or not installed.
               """
    batch_engine, vers = caris_command_finder('carisbatch.exe', (str(vers),), "HIPS")
    if not batch_engine:
        raise Exception("No Batch Engine found...is CARIS HIPS and SIPS {} installed?".format(vers))
    return batch_engine


def get_all_hips_versions():
    """
            Retrieves paths to the CARIS HIPS batch engine for all installed versions.

            Returns:
            --------
            list of tuples
                A list of tuples containing the full path to `carisbatch.exe` and the version number for each installed version.
                Each tuple is structured as (batch_engine, version_number).

            Raises:
            -------
            Exception
                If no CARIS HIPS and SIPS versions are found on the system.
                """
    versions = command_finder_hips(True)
    return versions


def command_finder_hips(get_all_versions=False):
    """
            Retrieves the CARIS HIPS batch engine path for the first installed version from a predefined list.

            The function searches through versions in the order provided, returning the path and version number for the first valid installation.

            Returns:
            --------
            tuple
                A tuple containing:
                - batch_engine : str
                    The full path to `carisbatch.exe` for the first valid CARIS HIPS version found.
                - vers : float
                    The version number of the found CARIS HIPS batch engine.

            Raises:
            -------
            Exception
                If no valid CARIS HIPS and SIPS version is found on the system.

            Example:
            --------
            >>> command_finder_hips()
            ('C:\\Program Files\\CARIS\\HIPS and SIPS 11.4\\bin\\carisbatch.exe', 11.4)
            """
    versions = caris_command_finder('carisbatch.exe', HIPS_VERSIONS, HIPS_NAME, get_all_versions=get_all_versions)
    # an empty return means nothing found but if get_all_versions is False then we get back a tuple of empty strings, so check the first index that too.
    # this covers the cases of [['C:\\Program Files\\CARIS\\HIPS and SIPS\\11.4\\bin\\carisbatch.exe', 11.4]] and []  for get_all_versions=True
    # vs  ['C:\\Program Files\\CARIS\\HIPS and SIPS\\11.4\\bin\\carisbatch.exe', 11.4] and ['', ''] for get_all_versions=False
    if not versions or not versions[0]:
        raise Exception("No Batch Engine found...is CARIS HIPS and SIPS installed?")
    return versions


def command_finder_base(get_all_versions=False):
    """
            Retrieves the CARIS BASE Editor batch engine path for the first installed version from a predefined list.

            The function searches through BASE Editor versions in the specified order and returns the path and version number for the first valid installation found.

            Returns:
            --------
            tuple
                A tuple containing:
                - batch_engine : str
                    The full path to `carisbatch.exe` for the first valid CARIS BASE Editor version found.
                - vers : float
                    The version number of the found CARIS BASE Editor batch engine.

            Raises:
            -------
            Exception
                If no valid CARIS BASE Editor version is found on the system.

            Example:
            --------
            >>> command_finder_base()
            ('C:\\Program Files\\CARIS\\BASE Editor 5.5\\bin\\carisbatch.exe', 5.5)
            """
    versions = caris_command_finder('carisbatch.exe', BASE_EDITOR_VERSIONS, BASE_EDITOR_NAME, get_all_versions=get_all_versions)
    # an empty return means nothing found but if get_all_versions is False then we get back a tuple of empty strings, so check the first index that too.
    if not versions or not versions[0]:
        raise Exception("No Batch Engine found...is CARIS BASE Editor installed?")
    return versions

__all__ = ['caris_command_finder', 'get_hips_command_from_version', 'get_all_hips_versions', 'command_finder_hips', 'command_finder_base',
           'HIPS_NAME', 'HIPS_VERSIONS', 'BASE_EDITOR_NAME', 'BASE_EDITOR_VERSIONS']
