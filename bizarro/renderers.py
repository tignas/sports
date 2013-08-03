import StringIO
import csv
import xlwt

class CSVRenderer(object):
    def __init__(self, info):
        pass

    def __call__(self, value, system):
        fout = StringIO.StringIO()
        writer = csv.writer(fout, delimiter=';', quoting=csv.QUOTE_ALL)

        writer.writerow(value['header'])
        writer.writerows(value['rows'])

        resp = system['request'].response
        resp.content_type = 'text/csv'
        resp.content_disposition = 'attachment;filename="report.csv"'
        return fout.getvalue()
        
import tablib


class TabLibBaseRendererFactory(object):
    def __init__(self, info):
        """init"""

    def __call__(self, value, system):
        request = system.get('request')
        if request is not None:
            response = request.response
            ct = response.content_type
            if ct == response.default_content_type:
                response.content_type = self.content_type
        response.content_disposition = 'attachment;filename="%s"' % value['filename']
        return value['data']


class XLSXRendererFactory(TabLibBaseRendererFactory):

    content_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'

    def __call__(self, value, system):
        data = super(XLSXRendererFactory, self).__call__(value, system)
        return data.xlsx


class XLSRendererFactory(TabLibBaseRendererFactory):

    content_type = 'application/vnd.ms-excel'

    def __call__(self, value, system):
        data = super(XLSRendererFactory, self).__call__(value, system)
        return data.xls


class CSVRendererFactory(TabLibBaseRendererFactory):

    content_type = 'text/csv'

    def __call__(self, value, system):
        data = super(CSVRendererFactory, self).__call__(value, system)
        return data.csv


class HTMLRendererFactory(TabLibBaseRendererFactory):

    content_type = 'text/html'

    def __call__(self, value, system):
        data = super(HTMLRendererFactory, self).__call__(value, system)
        return data.html
