import argparse
import sys
import spikeinterface.full as si

from PyQt5.QtWidgets import QWidget
from PyQt5.QtGui import QCloseEvent
import sys
from spikeinterface_gui.controller import Controller
from spikeinterface_gui.backend_qt import QtMainWindow

import functools # Useful for passing extra arguments, though not strictly required here
from pathlib import Path
from spikeinterface.core.core_tools import check_json
from copy import deepcopy
import pandas as pd


def my_custom_close_handler(event: QCloseEvent, window: QWidget, project_folder, save_folder, analyzer):
    """
    This function will be called instead of the original closeEvent.
    """
    print("Intercepted: User is trying to close the external window!")

    #from spikeinterface.curation import validate_curation_dict

    #curation_dict = check_json(window.controller.construct_final_curation())

    #validate_curation_dict(curation_dict)

    labelled_unit_ids = []
    labels = []

    print(f"{curation_dict['manual_labels']=}")

    for row in curation_dict['manual_labels']:
        print(f"{row=}")
        labelled_unit_ids.append(int(row['unit_id']))
        if row.get('labels') is None:
            labels.append(row['quality'][0])
        else:
            labels.append(row['labels']['quality'][0])

    qms = analyzer.get_extension("quality_metrics").get_data()
    tms = analyzer.get_extension("template_metrics").get_data()
    all_metrics = pd.concat([qms, tms], axis=1)

    labels_df = pd.DataFrame()
    labels_df['quality'] = labels

    labelled_metrics = all_metrics[all_metrics.index.isin(labelled_unit_ids)]

    all_metrics.to_csv(save_folder / "all_metrics.csv", index_label="unit_id")
    labelled_metrics.to_csv(save_folder / "labelled_metrics.csv", index_label="unit_id")
    labels_df.to_csv(save_folder / "labels.csv", index_label="unit_id")


argv = sys.argv[1:]

parser = argparse.ArgumentParser(description='spikeinterface-gui')
parser.add_argument('analyzer_folder', help='SortingAnalyzer folder path', default=None, nargs='?')
parser.add_argument('project_folder', help='Project folder path', default=None, nargs='?')
parser.add_argument('analyzer_index', help='Project folder path', default=None, nargs='?')

args = parser.parse_args(argv)

analyzer_folder = Path(args.analyzer_folder)
project_folder = Path(args.project_folder)
analyzer_index = int(args.analyzer_index)

save_folder = project_folder / (f"analyzers/{analyzer_index}_" + analyzer_folder.name)

if Path(save_folder / "labels.csv").is_file():
    decisions = pd.read_csv(save_folder / "labels.csv")
else:
    decisions = pd.DataFrame(columns=['unit_id', 'quality'])

print(f"{decisions=}")

analyzer = si.load_sorting_analyzer(analyzer_folder)

from spikeinterface.curation.curation_model import CurationModel

manual_labels = []
for unit_id in analyzer.unit_ids:
    decision = {"unit_id": unit_id, "quality": decisions[decisions['unit_id'] == unit_id]['quality'].values}
    if len(decision['quality']) > 0:
        manual_labels.append(decision)

label_definitions = {
    "quality": dict(name="quality", label_options=["good", "MUA", "noise"], exclusive=True),
}

curation_dict = dict(
    format_version="2",
    unit_ids=analyzer.unit_ids,
    manual_labels=manual_labels,
    label_definitions=label_definitions,
)

controller = Controller(
        analyzer, backend="qt", curation=True, curation_data=curation_dict, verbose=True
        #displayed_unit_properties = ["quality", "firing_rate", "num_spikes", "x", "y", "amplitude_median", "snr", "rp_violations"]
)

layout_dict={'zone1': ['unitlist'], 'zone2': [], 'zone3': ['waveform'], 'zone4': ['correlogram'], 'zone5': ['spikeamplitude'], 'zone6': [], 'zone7': [], 'zone8': ['spikerate']}

from pyqtgraph import mkQApp
app = mkQApp()
win = QtMainWindow(controller, layout_dict=layout_dict, user_settings=None)
win.closeEvent = functools.partial(my_custom_close_handler, window=win, project_folder=project_folder, save_folder=save_folder, analyzer=analyzer)

win.show()
app.exec()

print(f"{dir(win.controller)=}")

#win.show()


