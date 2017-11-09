#!/usr/bin/env python3
# Code for Item Catalog Database Setup
import os
import sys
from sqlalchemy import Column, ForeignKey, Integer, String

from sqlalchemy.ext.declarative import declarative_base

from sqlalchemy.orm import relationship

from sqlalchemy import create_engine

from sqlalchemy.sql import func
from sqlalchemy.types import DateTime

Base = declarative_base()


class User(Base):
    """User table class"""
    __tablename__ = 'user'
    id = Column(Integer, primary_key=True)
    name = Column(String(250), nullable=False)
    email = Column(String(250), nullable=False)
    picture = Column(String(250))


class Category(Base):
    """Category table class"""
    __tablename__ = 'category'
    id = Column(Integer, primary_key=True)
    name = Column(String(250), nullable=False)
    user_id = Column(Integer, ForeignKey('user.id'))
    user = relationship(User)

    @property
    def serialize_category(self):
        """
        Return object's relations in easily serializeable format.
        """
        return{
           'name': self.name,
           'id': self.id
           }


class Item(Base):
    """Category item table class"""
    __tablename__ = 'item'
    id = Column(Integer, primary_key=True)
    name = Column(String(80), nullable=False)
    description = Column(String(500))
    cat_id = Column(Integer, ForeignKey('category.id'))
    category = relationship(Category)
    user_id = Column(Integer, ForeignKey('user.id'))
    user = relationship(User)
    creation_date = Column(DateTime(timezone=True), server_default=func.now())


# Returns object data in serialized format
    @property
    def serialize(self):
        return {
            'name': self.name,
            'description': self.description,
            'id': self.id,
            'cat_id': self.cat_id
            }

# insert at end of file
engine = create_engine('sqlite:///itemcatalog.db')
Base.metadata.create_all(engine)
