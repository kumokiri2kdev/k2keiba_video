import logging
import logging.config

from k2kvideo import ocr


logging.config.fileConfig('logging.ini', disable_existing_loggers=False)
logger = logging.getLogger(__name__)


if __name__ == '__main__':

    races = [
        {
            'id': 'pw01sde1005201901041120190203/66',
            'laps' : [123, 109, 113, 112, 115, 113, 115,119]
        }
    ]

    for race in races:
        ocr = ocr.RpaJRAVideoReadTime(race['id'], rcw=True)
        output = ocr.find_snap_shop(race['laps'])

        for time_stamp in output:
            logging.info('ts : {} ({})'.format(time_stamp['ts'], time_stamp['time']))
            logging.info(' file : {}'.format(time_stamp['file']))


