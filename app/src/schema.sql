drop table if exists bogos;
create table bogos (
  id              integer    primary key autoincrement,
  sequence_length integer    not null,
  started         date       not null,
  finished        date
);

drop table if exists iterations;
create table iterations (
  id          integer primary key,
  bogo        integer not null,
  messiness   integer not null,
  foreign key(bogo) references bogos(id)
);

drop table if exists backups;
create table backups (
  id            integer primary key autoincrement,
  sequence      text    not null,
  random_state  text    not null,
  saved         date    not null
);

