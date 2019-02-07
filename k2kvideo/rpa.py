import os
import shutil
import logging.config
from time import sleep
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.common import exceptions
from selenium.webdriver.support.ui import WebDriverWait


FILE_PATH = '/tmp/k2kvideo_landing_page.html'
PIC_DIRE_PATH = './pic/{}'
SCREEN_SHOT_INTERVAL = 0.5

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

class RpaJRAVideoPlayTimeout(Exception):
    pass

class RpaJRAVideoPlayContentError(Exception):
    pass

class RpaJRAVideoPlayRetryTimeOut(Exception):
    pass

class RpaJRAVideoPlayObserveTimeout(Exception):
    pass

class RpaJRAVideoPlayFail(Exception):
    pass

class RpaJRAVideo(object):
    def get_driver(self):
        pass

    def safty_wait(self):
        sleep(0.5)

    def get_pic_dir_path(self):
        return self.pic_dir

    def gen_pic_dir(self, race_id):
        race_id = race_id.replace('/', '-')
        self.pic_dir = PIC_DIRE_PATH.format(race_id)
        if os.path.isdir(self.pic_dir):
            shutil.rmtree(self.pic_dir)

        os.mkdir(self.pic_dir)

    def gen_landing_page(self, race_id):
        with open(FILE_PATH, 'w') as wfp:
            template =  '<html>' \
                        '     <form action="http://www.jra.go.jp/JRADB/accessS.html" method="post">' \
                        '     <input type="hidden" name="cname" value="{}"/>' \
                        '     <input type="submit" value="POST" id="btn"/>'\
                        '     </form>'\
                        '</html>'\

            contents = template.format(race_id)
            wfp.write(contents)

    def invoke_jra_result(self):
        try :
            element_btn = self.browser.find_element_by_id('btn')
            element_btn.click()
        except exceptions.NoSuchElementException:
            raise RpaJRAVideoPlayContentError
        except Exception as e:
            logger.error(e)

    def invoke_jra_video(self):
        try:
            WebDriverWait(self.browser, 5).until(EC.presence_of_element_located((By.CLASS_NAME, 'movie_line')))
            element_movie_div = self.browser.find_element_by_class_name('movie_line')
            element_btn = element_movie_div.find_element_by_tag_name('a')
            element_btn.click()
        except exceptions.TimeoutException:
            raise RpaJRAVideoPlayTimeout
        except exceptions.NoSuchElementException:
            raise RpaJRAVideoPlayContentError


    def set_high_quality(self):
        try :
            WebDriverWait(self.browser, 30).until(EC.presence_of_element_located((By.CLASS_NAME, 'eq-icon-resolution')))
            resolution_btn = self.browser.find_element_by_class_name('eq-icon-resolution')
        except exceptions.TimeoutException:
            raise RpaJRAVideoPlayTimeout

        if resolution_btn.is_displayed():
            for i in range(10):
                try:
                    resolution_btn.click()
                    WebDriverWait(self.browser, 10).until(
                        EC.visibility_of_element_located((By.CLASS_NAME, 'eq-balloon-resolution')))
                    WebDriverWait(self.browser, 10).until(EC.element_to_be_clickable((By.CLASS_NAME, 'eq-balloon-item')))
                    eq_buttons = self.browser.find_elements_by_class_name('eq-balloon-item')
                    if len(eq_buttons) > 1:
                        eq_buttons[1].click()
                        break
                except exceptions.TimeoutException:
                    logger.info('TimeoutException')
                except exceptions.ElementClickInterceptedException:
                    logger.info('ElementClickInterceptedException')
                except exceptions.ElementNotInteractableException:
                    logger.info('ElementNotInteractableException')
                sleep(0.5)

            else:
                raise RpaJRAVideoPlayTimeout
        else:
            raise RpaJRAVideoPlayContentError

    def wait_until_video_plays(self):
        try:
            WebDriverWait(self.browser, 15).until(EC.invisibility_of_element((By.CLASS_NAME, 'eq-center-icon-loading')))
        except exceptions.TimeoutException:
            raise RpaJRAVideoPlayTimeout

    def observe_video(self):
        logger.info('Video Start')

        loading_timer = 0

        pic_dir = self.get_pic_dir_path()
        for i in range(480):
            try:
                WebDriverWait(self.browser, SCREEN_SHOT_INTERVAL).until(
                    EC.visibility_of_element_located((By.CLASS_NAME, 'eq-center-icon-replay')))
                break
            except exceptions.TimeoutException:
                self.browser.get_screenshot_as_file('{}/test_{:04d}.png'.format(pic_dir, i))
                try :
                    loading = self.browser.find_element_by_class_name('eq-center-icon-loading')
                    if loading == None or loading.is_displayed() == False:
                        loading_timer = 0
                    else:
                        logger.info('Loading Timer is shown')
                        loading_timer += 1
                except exceptions.NoSuchElementException:
                    loading_timer = 0

                if i % 10 == 0:
                    logger.info('Captured[{:04d}]'.format(i))

                if loading_timer > 20:
                    logger.error('Ugh Maybe Never End')
                    raise RpaJRAVideoPlayObserveTimeout
        else:
            logger.error('Ugh Never End')
            raise RpaJRAVideoPlayObserveTimeout

        logger.info('Video End')

    def play_jra_video(self):
        self.invoke_jra_video()

        self.safty_wait()

        handles = self.browser.window_handles

        self.browser.switch_to_window(handles[1])

        for i in range(3):
            try :
                WebDriverWait(self.browser, 5).until(EC.presence_of_element_located((By.TAG_NAME, 'iframe')))
                logger.debug('iframe comes up')
                iframe = self.browser.find_elements_by_tag_name('iframe')
                if len(iframe) >= 1:
                    logger.debug('switch')
                    self.browser.switch_to.frame(iframe[0])
                    break
                else:
                    logger.info("No iframe")
                    sleep(1)
            except exceptions.TimeoutException:
                logger.info('exceptions.TimeoutException happens, retry')
        else:
            self.browser.close()
            self.browser.switch_to_window(handles[0])
            raise RpaJRAVideoPlayTimeout

        self.set_high_quality()

        try:
            self.wait_until_video_plays()
        except RpaJRAVideoPlayTimeout:
            self.browser.close()
            self.browser.switch_to_window(handles[0])
            raise RpaJRAVideoPlayTimeout



    def automated_screen_shot(self):
        self.browser = self.get_driver()

        for i in range(5):
            self.browser.get('file:////{}'.format(FILE_PATH))
            self.safty_wait()
            try :
                self.invoke_jra_result()
                break
            except RpaJRAVideoPlayContentError:
                logger.info('Retry to load JRA Result')
        else:
            logger.error('Failed to play video')
            self.browser.close()
            self.browser.switch_to_window(self.browser.window_handles[0])
            self.browser.quit()
            raise RpaJRAVideoPlayFail

        self.safty_wait()

        for i in range(5):
            try :
                self.play_jra_video()
                break
            except RpaJRAVideoPlayTimeout:
                logger.info('Retry Play Video [{}]'.format(i))
            except RpaJRAVideoPlayContentError:
                logger.info('Retry Play Video [{}]'.format(i))
        else:
            logger.error('Failed to play video')
            self.browser.close()
            self.browser.switch_to_window(self.browser.window_handles[0])
            self.browser.quit()
            raise RpaJRAVideoPlayFail

        try :
            self.observe_video()
        except RpaJRAVideoPlayObserveTimeout:
            self.browser.close()
            self.browser.switch_to_window(self.browser.window_handles[0])
            self.browser.quit()
            logger.info('Retry Play Video [{}]'.format(i))
            raise RpaJRAVideoPlayFail

        self.browser.close()
        self.browser.switch_to_window(self.browser.window_handles[0])
        self.browser.quit()


    def start_automated_process(self, race_id):
        self.gen_landing_page(race_id)
        self.gen_pic_dir(race_id)

        self.automated_screen_shot()


class RpaJRAVideoFireFox(RpaJRAVideo):
    def get_driver(self):
        return webdriver.Firefox()





