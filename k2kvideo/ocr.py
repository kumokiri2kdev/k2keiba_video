import glob
import os.path
import logging.config

import cv2
import numpy as np
from sklearn.externals import joblib

logging.config.dictConfig({
    'version': 1,
    'formatters': {
        'k2k_formatter': {
            'format': '[%(filename)s:%(lineno)03d] %(message)s'
        },
    },
    'handlers': {
        'k2k_handler': {
            'class': 'logging.StreamHandler',
            'formatter': 'k2k_formatter'
        }
    },
    'loggers': {
        'k2kparser': {
            'handlers': ['k2k_handler'],
            'level': logging.INFO,
            'propagate': 0
        }
    }
})
logger = logging.getLogger(__name__)

class RpaJRAVideoReadTime():
    TIME_SEG = {
        'top': 42,
        'bottom': 82,
        'left': 70,
        'right': 168 + 26 + 11
    }

    TIME_SEG_RCW_OFFSET = 996

    UNIT_HIGHT = TIME_SEG['bottom'] - TIME_SEG['top']
    UNIT_WIDTH = 26

    BASE_OFFSET = 72 + 11 + 26
    FIRST_SEGMENT_OFFSET = 0
    SECOND_SEGMENT_OFFSET = FIRST_SEGMENT_OFFSET + 11 + UNIT_WIDTH
    THIRD_SEGMENT_OFFSET = (SECOND_SEGMENT_OFFSET + UNIT_WIDTH)
    FORTH_SEGMENT_OFFSET = (THIRD_SEGMENT_OFFSET + 11 + UNIT_WIDTH)

    PIC_DIRE_PATH = './pic'

    def __init__(self, race_id, rcw=False):
        if rcw:
            self.offset = self.TIME_SEG_RCW_OFFSET
        else:
            self.offset = 0

        self.race_id = race_id.replace('/', '-')

        filename = 'finalized_model.sav'
        if os.path.isfile(filename) == False:
            import k2kvideo
            if type(k2kvideo.__path__) == list:
                filename = '{}/assets/{}'.format(k2kvideo.__path__[0], filename)
                if os.path.isfile(filename) == False:
                    logging.error('Serialized file "{}" not found'.format(filename))
                    # ToDo Raise an error
            else:
                logging.error('Serialized file "{}" not found'.format(filename))
                # ToDo Raise an error

        logging.debug('Serialized File : {}'. format(filename))

        self.clf = joblib.load(filename)


    def read_from_file(self, filename):
        img = cv2.imread(filename, 1)
        img = img[
                self.TIME_SEG['top']: self.TIME_SEG['bottom'],
                self.TIME_SEG['left'] + self.offset: self.TIME_SEG['right'] + self.offset
              ]

        img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        digits = []

        digits.append(img_gray[0:self.UNIT_HIGHT,
                      self.BASE_OFFSET - self.FIRST_SEGMENT_OFFSET - 1:
                      len(img_gray[0]) - self.FIRST_SEGMENT_OFFSET - 1])
        digits.append(img_gray[0:self.UNIT_HIGHT,
                      self.BASE_OFFSET - self.SECOND_SEGMENT_OFFSET - 1:
                      len(img_gray[0]) - self.SECOND_SEGMENT_OFFSET - 1])
        digits.append(img_gray[0:self.UNIT_HIGHT,
                      self.BASE_OFFSET - self.THIRD_SEGMENT_OFFSET - 1:
                      len(img_gray[0]) - self.THIRD_SEGMENT_OFFSET - 1])
        digits.append(img_gray[0:self.UNIT_HIGHT,
                      self.BASE_OFFSET - self.FORTH_SEGMENT_OFFSET - 1:
                      len(img_gray[0]) - self.FORTH_SEGMENT_OFFSET - 1])

        img_tgt = np.array(digits).reshape((-1, self.UNIT_HIGHT * self.UNIT_WIDTH))
        predicts = (self.clf.predict(img_tgt))


        time = ''
        time_int = 0
        is_additinal_digit = False

        if predicts[3] != 'o':
            time += predicts[3] + '.'
            time_int += int(predicts[2]) * 60

        if predicts[2] != 'o':
            time += predicts[2]
            time_int += int(predicts[1]) * 10

        if predicts[1] != 'o':
            time += predicts[1]
            time_int += int(predicts[1])

        if predicts[0] != 'o':
            is_additinal_digit = True

        return time, time_int, is_additinal_digit



    def read_time(self):

        files = sorted(glob.glob('{}/{}/*.png'.format(self.PIC_DIRE_PATH, self.race_id)))

        self.time_stamps = []

        for file in files:
            time, time_int, is_addtional_digit = self.read_from_file(file)
            logger.debug('Time : {}. Sec : {}'.format(time, time_int))
            time_stamp = {
                'file': file,
                'ts': time_int,
                'time': time
            }

            if is_addtional_digit:
                time_stamp['additional'] = True

            self.time_stamps.append(time_stamp)

        return self.time_stamps

    def find_snap_shop(self, laps):
        time_output = []

        self.read_time()

        for i in range(0, len(self.time_stamps)):
            if self.time_stamps[i]['ts'] >= 1 :
                time_output.append(self.time_stamps[i])
                del self.time_stamps[:i+1]
                break

        elapsed_time = 0
        for lap in laps:
            elapsed_time += lap
            second = int(elapsed_time / 10)
            for i in range(0, len(self.time_stamps)):
                if self.time_stamps[i]['ts'] >= second:
                    time_output.append(self.time_stamps[i])
                    del self.time_stamps[:i + 1]
                    break


        return time_output

    def get_histg(self, file):
        img = cv2.imread(file)

        histg = cv2.calcHist([img], [2], None, [256], [0, 256])

        return histg

    def find_scene_start(self, files):
        files.reverse()

        histg_p = None

        for i, file in enumerate(files):
            histg_c = self.get_histg(file)
            if histg_p is not None:
                histg_diff = cv2.compareHist(histg_c, histg_p, cv2.HISTCMP_CORREL)
                if histg_diff < 0.6:
                    return files[i-1]

            histg_p = histg_c

    def get_trimed_list(self):
        time_output = []

        files = sorted(glob.glob('{}/{}/test_*.png'.format(self.PIC_DIRE_PATH, self.race_id)))

        initial_index  = -1

        for i, filename in enumerate(files):
            timestamp, timestamp_ss, is_additional_digit = self.read_from_file(filename)
            if timestamp_ss >= 1:
                initial_index = i
                initial_index = 0 if initial_index < 0 else initial_index

                scene_start = self.find_scene_start(files[:initial_index])
                initial_index = files.index(scene_start)

                break

        return files[initial_index:-1]
