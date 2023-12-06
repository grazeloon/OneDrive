from tqdm import tqdm
from time import sleep

total = 500
count = 0
pbar = tqdm(total=total)

while True:
    if count == 500:
        break
    else:
        sleep(0.1)
        count +=1
        pbar.update(1)
pbar.close()