import ast
import operator

COMMANDS = {}
COMMAND_ALIASES = {}

COMMAND_CATEGORIES = {
    "encryption": ["encrypt", "decrypt"],
    "general": ["run-as-admin", "cd", "cwd", "tree", "info", "aliases", "clear", "exit"],
    "utility": ["mode", "set-preference", 'rsa', 'benchmark'],
    "misc": ['ascii-art',"echo",'#']
}

COMMAND_DESCRIPTIONS = {
    "clear": "Clears the terminal screen.",
    "exit": "Exits Enigmatrix.",
    "run-as-admin" : ("Relaunches Enigmatrix with admin privileges."),
    "aliases" : ("Shows all the aliases for the given command name"),
    "ascii-art": ("Displays the \"Enigmatrix\" ASCII art on the screen\n"
                  "--clear -> Clears the screen and then displays the ASCII art of \"Enigmatrix\"."),
    "encrypt": ("Encrypts a file. \nUsage: encrypt <input_path> <output_path> <key> [rsa_file_path]\n"
                "or :   ecnrypt --input <path> --output <path> --key <key> [--rsa file_path]\n\n"
                "Legend:\n"
                "<> -> Required\n"
                "[] -> Optional"),
    "decrypt": ("Usage: decrypt <input_path> <output_path> [key] [rsa_file_path]\n"
                "or :   decrypt --input <path> --output <path> [--key key] [--rsa file_path]\n\n"
                "Legend:\n"
                "<> -> Required\n"
                "[] -> Optional / Conditional"),
    "tree": ("Displays directory structure.\n"
             "--depth -> set depth of the tree.\n"
             "Usage:\n"
             "tree [\"path/to/directory\"] --depth [number]\n"
             "Notes:\n"
             "- Both the path and depth options are optional\n"
             "- Default path is current working directory (use cwd to know)\n"
             "- Default depth of a tree is 3"),
    "cd": "Changes the current working directory.",
    "cwd": "Displays the current working directory.",
    "rsa-key" : ("Operations related to RSA key\n\n"
                 "--generate mykey\n"
                "Generates an RSA key pair with name \"mykey\"\n\n"
                 
                "--setdir \"C:\MyKeys\"\n"
                "Sets \"C:\MyKeys\" as RSA directory.\n\n"

                "--set mykey.pem\n"
                "Selects \"mykey.pem\" as RSA key file.\n\n"

                "--show\n"
                "Shows RSA directory and available key files in RSA directory"),
    "mode": ("Sets UI and Window mode:\n\n"
             "UI modes: \n"
             "--terminal -> Only terminal part is visible and GUI is hidden.\n"
             "--ui -> GUI panel is visible along with terminal.\n\n"
             "Window mode: \n"
             "--fullscreen\n"
             "--maximize\n"
             "--normal\n"
             "--small\n"),
    "set-preference" : ("Usage: set-preference --<category> <option>\n"
                        "The set-preference command allows configuring UI, window, and performance preferences. It stores settings and applies them immediately and every time Enigmatrix is launched.\n\n"
                        "UI Preferences:\n"
                        "--ui terminal -> Only the terminal is visible, GUI is hidden.\n"
                        "--ui gui -> GUI panel is visible alongside the terminal.\n\n"
                        "Window Preferences:\n"
                        "--window fullscreen\n"
                        "--window maximize\n"
                        "--window normal\n"
                        "--window small\n\n"
                        "Performance Preferences:\n"
                        "--cores <number> -> Sets the number of CPU cores used for encryption/decryption.\n"
                        "   Example: --cores 4 (Uses 4 CPU cores for operations)\n"
                        "   Minimum: 2 | Maximum: Based on your system's CPU count.\n\n"
                        "Example Usage:\n"
                        "set-preference --ui terminal --window fullscreen --cores 4\n"
                        "Changes preference to full terminal mode, fullscreen window, and 4 CPU cores for processing every time you launch Enigmatrix.\n\n"
                        "Note: Using --default will reset preferences to the app's default settings."),
    "benchmark" : ("Measures encryption performance by testing encryption speed on a 100MB file.\n"
                   "Runs a performance benchmark to evaluate Enigmatrix's encryption speed. \n"
                   "The benchmark encrypts a 100MB test file and measures the total time taken.\n"
                   "This helps users understand the expected encryption speed on their system.\n"
                   "The benchmark automatically uses an optimized number of CPU cores (total // 2)\n"
                   "to ensure balanced performance.\n"
                   "Notes: \n"
                   "    - The test file is automatically generated and deleted after benchmarking.\n"
                   "    - This command does not affect any user files."),
    "info" : ("Displays Enigmatrix configuration info, including CPU cores used and current version.\n"
              "--cores   -> shows the number of cores used by encryption/decryption process\n"
              "--version -> shows the current version of Enigmatrix.\n"
              "--config  -> Displays the stored configuration settings."),
    "echo" : ("Simply prints the given text to terminal.\n"
              "try \"echo Hello, World!\""),
    "print" : ("Simply prints the given text to terminal.\n"
              "try \"print Hello, World!\""),
    "say" : ("Simply prints the given text to terminal.\n"
              "try \"say Hello, World!\""),
    "#" : ("Use as a comment (does absolutely nothing)")
}

# Allowed operators
SAFE_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Mod: operator.mod,
    ast.BitOr: operator.or_,
    ast.BitAnd: operator.and_,
    ast.BitXor: operator.xor,
    ast.LShift: operator.lshift,
    ast.RShift: operator.rshift,
    ast.Invert: operator.inv,
    ast.USub: operator.neg,
}
