# Running the dataverse_utils scripts under Windows

On Mac and Linux, running the scripts supplied with `dataverse_utils` is straightforward. They're available at the command line, which means that you can simply run them by (for example):

`$ dv_manifest_gen.py` followed by switches and variables as normal.

Doing this results in output to the terminal window. **This is not necessarily the case in Windows**.

This test case uses a new installation of <https://python.org> Python, v.3.9.6, installed in Windows using the GUI, so it's as basic a Windows installation as you can get.

In this instance, `dataverse_utils` were installed using pip from the PowerShell, ie `pip install git+https://github.com/ubc-library-rc/dataverse_utils`. However, pip should be pip regardless of which console you use to install.

Here's a handy guide to show the results of how/if the command line scripts run. This example uses `dv_manifest.gen.py`, but appears to be generally applicable to any script installed using pip (ie, `scripts` in `setup.py`). If this means nothing to you, just skip to the table below.

## Terminal type

### Windows PowerShell

Note that on these tests the user **is not an administrator**. Administrator results, in all likelihood, will be completely different.

**Problem**

Attempting to run the script results in a window popping up for a nanosecond and no output.

**Solution**

1. This may not occur if the PowerShell is run as an administrator. What is happening here is that the script *is* running, but it's showing up in a separate window.  Output can be created as normal, if you use the correct switches. Unfortunately, you won't be able to see what they are, because the popup window disappears, which is not helpful.

	A solution is to edit the PATHEXT environment variable to include the .py extension. Note that if the **user** PATHEXT is edited, the system will ignore the system PATHEXT, meaning that things like .exe files won't run unless the full name is typed (eg. 'notepad.exe'). So, if editing the user PATHEXT, make sure to include the system PATHEXT and append `;.PY` to the string.

2. Another potential solution is to edit the PATHEXT for just PowerShell itself. Editing $PROFILE to include the .py extension should allow the Python script to run within PowerShell. For instructions, see <https://docs.microsoft.com/en-ca/powershell/module/microsoft.powershell.core/about/about_profiles?view=powershell-7.1>.

	1. Create a profile as per **How to create a profile**

	2. Within that profile, `$env:PATHEXT += ";.py"`

	Depending on the nature of your Windows installation, this may be disabled by security policy, in which case you can also try the method above.

### Command Prompt

This is the traditional Windows command prompt (ie, `cmd.exe`).

The scripts *should* just work after being installed with pip. For example, run with:

`C:\>dv_manifest_gen.py [arguments]`

Obviously it don't type the `C:\>` part.

### SSH session

If using the built-in Windows SSH server, scripts should simply run as per the Command Prompt above. I didn't see that coming.

### Git Bash

*Git Bash* is part of the git suite available here: <https://git-scm.com/downloads>. There are a few notable wrinkles with for use with Python.

**During installation**

After 05 August 2021 (the date of testing), you will have the option during the installation to "Enable experimental support for pseudo consoles". If you have enabled the experimental support, then this is not required, although you may run into bugs from the experimental support feature. However, enabling this feature seems to fix errors with pipes which formerly resulted in the `stdout is not a tty` error. There is no right choice here.

If you have *not* checked this box, you will need to add an alias to your `.bashrc` and/or `.bash_profile`:

`alias python='winpty python'`
`alias pip='winpty pip'`

Without this, Python will not start at all and hang at the prompt.
