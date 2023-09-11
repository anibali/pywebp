import logging


def _create_logger():
    logger = logging.getLogger(__name__)
    logger.propagate = False
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    return logger


logger = _create_logger()
