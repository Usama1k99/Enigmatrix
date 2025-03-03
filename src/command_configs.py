import ast
import operator

COMMANDS = {}
COMMAND_ALIASES = {}

COMMAND_CATEGORIES = {
    "encryption": ["encrypt", "decrypt"],
    "general": ["cd", "cwd", "tree", "clear", "exit"],
    "utility": ["mode", "set-preference", 'rsa'],
    "misc": ['ascii-art']
}

COMMAND_DESCRIPTIONS = {
    "clear": "Clears the terminal screen.",
    "exit": "Exits Enigmatrix.",
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
    "tree": "Displays directory structure.",
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
                        "The set-preference command allows configuring UI and window preferences. It stores settings and applies them immediately and everytime Enigmatrix is launched.\n\n"
                        "UI preferences: \n"
                        "--ui terminal -> Only the terminal is visible, GUI is hidden.\n"
                        "--ui gui -> GUI panel is visible alongside the terminal\n\n"
                        "Window Preferences:\n"
                        "--window fullscreen\n"
                        "--window maximize\n"
                        "--window normal\n"
                        "--window small\n\n"
                        "Example usage: \n"
                        "set-preference --ui terminal --window fullscreen\n"
                        "Changes preference to full terminal and fullscreen mode everytime you launch Enigmatrix.")
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
