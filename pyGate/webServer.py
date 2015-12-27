__author__ = 'Jan Bogaerts'
__copyright__ = "Copyright 2015, AllThingsTalk"
__credits__ = []
__maintainer__ = "Jan Bogaerts"
__email__ = "jb@allthingstalk.com"
__status__ = "Prototype"  # "Development", or "Production"

from flask import Flask

app = Flask(__name__)

def run():
    app.run(host='0.0.0.0', debug=False, threaded=True)



@app.route('/<path:path>')
def catch_all(path):
    return 'You want path: %s' % path