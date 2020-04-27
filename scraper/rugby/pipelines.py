# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: http://doc.scrapy.org/en/latest/topics/item-pipeline.html

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.engine.url import URL

from scrapy.exporters import CsvItemExporter

from rugby import models, items, settings

class RugbyScraperPipeline(object):
    def __init__(self):
        """"""
        # Connect to DB
        self.engine = create_engine(self._get_db_url())
        self.session = sessionmaker(bind = self.engine)
        models.create_tables(self.engine)

    def _get_db_url(self):
        return "sqlite:///" + settings.SQLITE_ABS_PATH

    def open_spider(self, spider):
        self.logger = spider.logger

    def process_item(self, item, spider):
        """"""
        session = self.session()
        instance = None
        try:
            if isinstance(item, items.Match):
                self._unique_insert(session, models.Match, item)
            elif isinstance(item, items.Player):
                self._unique_insert(session, models.Player, item)
            elif isinstance(item, items.Team):
                self._unique_insert(session, models.Team, item)
            elif isinstance(item, items.MatchStats):
                self._insert_or_update(session, models.MatchStats, item, match_id=item["match_id"], team_id=item["team_id"])
            elif isinstance(item, items.MatchExtraStats):
                self._generic_insert(session, models.MatchExtraStats, item)
            elif isinstance(item, items.PlayerStats):
                self._insert_or_update(session, models.PlayerStats, item, player_id=item["player_id"], team_id=item["team_id"], match_id=item["match_id"])
            elif isinstance(item, items.PlayerExtraStats):
                self._generic_insert(session, models.PlayerExtraStats, item)
            elif isinstance(item, items.GameEvent):
                self._generic_insert(session, models.GameEvent, item)
            session.commit()
        except Exception as e:
            session.rollback()
            self.logger.error("Error while committing to DB : {}".format(e))
        finally:
            session.close()

        return item

    def _generic_insert(self, session, model, item):
        if not model or not item:
            return
        self.logger.info("Inserting entry of type \"{}\" in DB".format(item.__class__.__name__))
        return session.add(model(**item))

    def _unique_insert(self, session, model, item):
        if not model or not item:
            return
        instance = model(**item)

        if not session.query(model).filter(model.id == instance.id).first():
            return self._generic_insert(session, model, item)
        else:
            self.logger.info("\"{}\" already existing in DB".format(item.__class__.__name__))

    def _insert_or_update(self, session, model, item, **filters):
        if not model or not item:
            return

        result = session.query(model).filter_by(**filters).first()

        if not result:
            return self._generic_insert(session, model, item)
        else:
            session.query(model).filter_by(**filters).update(item)
            self.logger.info("Updating \"{}\" item.".format(item.__class__.__name__))




class RpiScraperCSVPipeline(object):

    #def __init__(self):
        #self.file = open("data.csv", 'wb')
        #self.exporter = CsvItemExporter(self.file)
        #self.exporter.start_exporting()

    def open_spider(self, spider):
        self.itemtype_to_exporter = {}
        self.files = {}

    def close_spider(self, spider):
        print((self.files))
        print(self.itemtype_to_exporter.keys())
        for exporter in self.itemtype_to_exporter.values():
            exporter.finish_exporting()
        for file in self.files.values():
            print('file closed')
            file.close()
            

    def _exporter_for_item(self, item):
        item_type = type(item).__name__
        if item_type not in self.itemtype_to_exporter:
            f = open(f"{item_type}.csv", 'wb')
            exporter = CsvItemExporter(f)
            exporter.start_exporting()
            self.itemtype_to_exporter[item_type] = exporter
            self.files[item_type] = f
        return self.itemtype_to_exporter[item_type]

    def process_item(self, item, spider):

        exporter = self._exporter_for_item(item)
        exporter.export_item(item)

        return item

