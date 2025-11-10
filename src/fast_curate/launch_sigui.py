import argparse
import sys
import spikeinterface.full as si
from spikeinterface_gui import run_mainwindow

from PyQt5.QtWidgets import QMainWindow, QWidget, QApplication, QMessageBox
from PyQt5.QtGui import QCloseEvent
import sys
import functools # Useful for passing extra arguments, though not strictly required here

argv = sys.argv[1:]

parser = argparse.ArgumentParser(description='spikeinterface-gui')
parser.add_argument('analyzer_folder', help='SortingAnalyzer folder path', default=None, nargs='?')

args = parser.parse_args(argv)

analyzer_folder = args.analyzer_folder

analyzer = si.load_sorting_analyzer(analyzer_folder)


def my_custom_close_handler(event: QCloseEvent, window: QWidget):
    """
    This function will be called instead of the original closeEvent.
    """
    print("Intercepted: User is trying to close the external window!")
    
    # --- Put your 'do something' logic here ---
    
    # Example: Ask for confirmation
    reply = QMessageBox.question(window, 'Confirm Close',
        "Do you really want to close this window?", 
        QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

    if reply == QMessageBox.Yes:
        # Important: Allow the window to close
        print("Closing the window.")
        event.accept()
    else:
        # Important: Prevent the window from closing
        print("Closing blocked.")
        event.ignore()

win = run_mainwindow(
    analyzer,
    curation=True,
)

win.closeEvent = functools.partial(my_custom_close_handler, window=win)
