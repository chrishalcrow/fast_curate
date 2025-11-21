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

    # from spikeinterface.curation import validate_curation_dict

    # curation_dict = check_json(window.controller.construct_final_curation())

    # validate_curation_dict(curation_dict)

    # labelled_unit_ids = []
    # labels = []

    # print(f"{curation_dict['manual_labels']=}")

    # for row in curation_dict['manual_labels']:
    #     print(f"{row=}")
    #     labelled_unit_ids.append(int(row['unit_id']))
    #     labels.append(row['quality'][0])


    # qms = analyzer.get_extension("quality_metrics").get_data()
    # tms = analyzer.get_extension("template_metrics").get_data()
    # all_metrics = pd.concat([qms, tms], axis=1)

    # labelled_qms = deepcopy(all_metrics.iloc[labelled_unit_ids])
    # labelled_qms['quality'] = labels

    # print(f"{labelled_qms=}")

#    labelled_qms.to_csv(save_folder / "decision_data_with_metics.csv", index_label="unit_id")

    # num_units = str(analyzer.get_num_units())
    # with open(save_folder / "num_units.txt", 'w') as f:
    #     f.write(num_units)


argv = sys.argv[1:]

parser = argparse.ArgumentParser(description='spikeinterface-gui')
parser.add_argument('analyzer_folder', help='SortingAnalyzer folder path', default=None, nargs='?')
parser.add_argument('project_folder', help='Project folder path', default=None, nargs='?')
parser.add_argument('analyzer_in_project', help='Project folder path', default=None, nargs='?')
parser.add_argument('model_predictions_file')

args = parser.parse_args(argv)

analyzer_folder = Path(args.analyzer_folder)
project_folder = Path(args.project_folder)
analyzer_in_project = Path(args.analyzer_in_project)
model_predictions_file = Path(args.model_predictions_file)

save_folder = project_folder / analyzer_in_project
save_folder.mkdir(exist_ok=True, parents=True)

model_decisions = pd.read_csv(model_predictions_file)

analyzer = si.load_sorting_analyzer(analyzer_folder)

manual_labels = []
for unit_id in analyzer.unit_ids:
    decision = {"unit_id": unit_id, 
                "model": model_decisions[model_decisions['unit_id'] == unit_id]['prediction'].values,
                }
    if len(decision['model']) > 0:
        manual_labels.append(decision)
    

label_definitions = {
    "quality": dict(name="quality", label_options=["good", "MUA", "noise"], exclusive=True),
    "model": dict(name="model", label_options=["good", "MUA", "noise"], exclusive=True),
}

curation_dict = dict(
    format_version="2",
    unit_ids=analyzer.unit_ids,
    manual_labels=manual_labels,
    label_definitions=label_definitions,
)

controller = Controller(
        analyzer, backend="qt", curation=True, curation_data=curation_dict, verbose=True,
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


