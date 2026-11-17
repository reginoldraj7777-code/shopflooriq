"""Start a fresh, uniquely named recording database; never reset an existing one."""
import argparse
from datetime import datetime
from uuid import uuid4
from shopflooriq.store import ROOT
from shopflooriq.server import serve


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port',type=int,default=8766)
    args=parser.parse_args()
    folder=ROOT/'data'/'recordings';folder.mkdir(parents=True,exist_ok=True)
    path=folder/f"recording-{datetime.now():%Y%m%d-%H%M%S}-{uuid4().hex[:8]}.sqlite"
    # Exclusive creation makes the preservation guarantee explicit, even on collision.
    with path.open('xb'):
        pass
    print(f"Fresh recording database: {path}\nOriginal database is unchanged.",flush=True)
    serve(path,args.port)


if __name__=='__main__':
    main()
