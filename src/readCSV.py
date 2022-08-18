import csv
from collections import namedtuple


ROW = namedtuple('StockCodeInfo', ['type', 'code', 'name', 'ISIN', 'start',
                                   'market', 'group', 'CFI'])


def read_csv(path, name):
    with open(path, newline='', encoding='utf_8') as csvfile:
        reader = csv.reader(csvfile)
        csvfile.readline()
        for row in reader:
            row = ROW(*(item.strip() for item in row))
            #codes[row.code] = row
            if row.name==name:
                 return row.code

            # if types == 'tpex':
            #     tpex[row.code] = row
            # else:
            #     twse[row.code] = row


#read_csv(TPEX_EQUITIES_CSV_PATH, 'tpex')
#read_csv(TWSE_EQUITIES_CSV_PATH, 'twse')