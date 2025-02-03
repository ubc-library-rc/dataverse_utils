# Frequently asked questions

"Frequently" may be relative.

## 1. I'm using Windows and the scripts don't seem to be working/recognized by [choice of command line interface here]

There are (at least) four different ways to get some sort of command line access (actually a lot more than four but these are common). The traditional command line, PowerShell, via SSH and Git Bash. That's not even including the linux subsystem. Each of these may not be share the same environment as any other. 

The document on [Windows script troubles](windows.md) gives common solutions.

## 2. I am using Windows [7-10]. I've installed via pip using a virtual environment, but they don't use my virtual environment's Python.

What seems like a simple problem is surprisingly complex, as outlined here: <https://matthew-brett.github.io/pydagogue/installing_scripts.html>.

This is further complicated by some other factors.

* If you have only one Python installation on your machine, you are probably OK. Mind you, if you're looking at this and that's the case, maybe I'm wrong.

* If you have multiple Pythons, you can try changing your environment variables to point to the correct Python.

* If you are using ArcGIS products, ArcGIS may write items into your Windows registry which will associate any .py file with it's grossly outdated Python 2.7, or just the wrong Python.

  More specifically: `Computer\HKEY_CLASSES_ROOT\Python.File\shell\open\command` in the Windows registry. Unfortunately, the Windows computer that I have available for testing (as I normally use Linux or Mac) does not have an administrator account, so I can't confirm that changing this key will work (although there's no reason to believe it won't).

### This is a pain. Is there something less irritating that would work?

* Yes, there is. You can still run the scripts manually. There are two options for this.

	* Download the repository via git to a convenient place and use the files in the `scripts/` directory

	* Point your %PATH% to where the scripts are installed. To find out *where* they are installed:

	    TLDR: version: Point your %PATH% (and use first part of the path) to point to your `[venv]\Scripts` directory, because they're probably there.

	     Long winded instructions/explanation:

	     Start a Python session:

		import sys
		sys.path
		[x for x in sys.path if x.endswith('site-packages')]
	
	     The location of the scripts will be written in `[whatever the output of sys.path]/dataverse_utils[somestuff]egg-info/installed-files.txt`, usually three levels up in the `scripts` directory.

	     Ironically, this is also the location of the `activate` portion of the comand required to start a virtual environment (if you are using a virtual environment).


	For some background on this, `venv` in Linux and Mac versions of Python uses `bin`, and reserves scripts for the `scripts` directory. Windows, however, uses `Scripts` for the `venv` module, and to make it worse it's not usually case sensitive, so anything in `scripts` gets put into `Scripts`.
 

