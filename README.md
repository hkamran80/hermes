# Project Hermes
## What is "Project Hermes"?
Project Hermes is a password-retrieval system, designed for extracting *browser* passwords from any computer. I am designing this system for myself, as I need to migrate all of my computers' saved passwords, over to a central machine.

## How Do I Run Project Hermes?
Make sure you have the following items:    
* Python 2.7
* Platform-specific
    * Windows:
        * [`pywin32`](https://sourceforge.net/projects/pywin32/files/latest/download)

Clone this repository to your computer, open the folder, and run the `main.py` file, with `python main.py`

## FAQ
### Why Python 2?
None of the machines that I need to get passwords off have Python 3. macOS has Python 2.7 pre-installed. This is why there is a **seperate** branch for Python 2, and Python 3. The Python 2 code was ported using [`3to2`](https://pypi.org/project/3to2/).

*This code only works on Darwin-based (macOS) systems, at the moment*
# Disclaimer
I am not responsible for any action caused by ANY code in this repository!

# License
This repository, and the code in it, is licensed under the GNU General Public License v3.0 license.
