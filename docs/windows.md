# Running the dataverse_utils scripts under Windows

On Mac and Linux, running the scripts supplied with `dataverse_utils` is straightforward. They're available at the command line, which means that you can simply run them by (for example):

`$ dv_manifest_gen.py` followed by switches and variables as normal.

Doing this results in output to the terminal window. **This is not necessarily the case in Windows**.

This test case uses a new installation of <https://python.org> Python, v.3.9.6, installed in Windows using the GUI, so it's as basic a Windows installation as you can get.

In this instance, `dataverse_utils` were installed using pip from the PowerShell, ie `pip install git+https://github.com/ubc-library-rc/dataverse_utils`. However, pip should be pip regardless of which console you use to install.

Here's a handy guide to show the results of how/if the command line scripts run. This example uses `dv_manifest.gen.py`, but appears to be generally applicable to any scripts configured with setuptools.setup()  (ie, `setuptools.setup(scripts=[whatever]`). If this means nothing to you because you're not distributing your own Python packages,, just skip to the table below.

## Windows Terminal type

### PowerShell

Note that on these tests the user **is not an administrator**. Administrator results, in all likelihood, will be completely different.

**Problem**

Attempting to run the script results in a window popping up for a nanosecond and no output.

**Solution**

This may not occur if the PowerShell is run as an administrator. What is happening here is that the script *is* running, but it's showing up in a separate window.  Output can be created as normal, if you use the correct switches. Unfortunately, you won't be able to see what they are, because the popup window disappears, which is not helpful. There are three potential fixes.

1. If you can run PowerShell as an administrator, that *may* solve the problem.

2. Edit the PATHEXT environment variable to include the .py extension. Note that if the **user** PATHEXT is edited, the system will ignore the system PATHEXT, meaning that things like .exe files won't run unless the full name is typed (eg. 'notepad.exe'). So, if editing the user PATHEXT, make sure to include the system PATHEXT and append `;.PY` to the string.

2. Edit the PATHEXT for PowerShell itself, rather than on a system wide level. Editing $PROFILE to include the .py extension should allow the Python script to run within PowerShell. For instructions, see <https://docs.microsoft.com/en-ca/powershell/module/microsoft.powershell.core/about/about_profiles?view=powershell-7.1>.

	1. Create a profile as per **How to create a profile**

	2. Within that profile, `$env:PATHEXT += ";.py"`

	Depending on the nature of your Windows installation, this may be disabled by the security policy, in which case you can also try the method above.

### Command prompt

This is the traditional Windows command prompt (ie, `cmd.exe`).

The scripts *should* just work after being installed with pip. For example, run with:

`C:\>dv_manifest_gen.py [arguments]`

Obviously it don't type the `C:\>` part.

### SSH session

If using the built-in Windows SSH server, scripts should simply run as per the *command prompt* above. I didn't see that coming.

### Git Bash

*Git Bash* is part of the git suite available here: <https://git-scm.com/downloads>. There are a few notable wrinkles with for use with Python.

**During installation of Git**

1. After v2.32.0.2 (and possibly earlier), you will have the option during the installation to "Enable experimental support for pseudo consoles". Doing this will allow you run Python directly from the bash shell like you would noraally, and the scripts should function as per the *command prompt* above. 

	As a bonus,  enabling this feature seems to fix errors with pipes which formerly resulted in the `stdout is not a tty` error when piping shell output (for instance, to `grep`). 

2. If you have *not* checked this box, you will need to add an alias to your `.bashrc` and/or `.bash_profile`:

	`alias python='winpty python'`
	`alias pip='winpty pip'`

	Either that, or you will need to start Python with `winpty python`, which is annoying. Similarly `winpty pip`. 

Even if you have not enabled pseudo-console support and didn't complete use option 2, the scripts *should* still function normally though. Having scripts work but Python not work is not optimal and confusing, so a solution is there even though it technically isn't required.
