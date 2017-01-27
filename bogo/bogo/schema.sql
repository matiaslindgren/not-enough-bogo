drop table if exists bogos;
create table bogos (
  id              integer    primary key autoincrement,
  sequence_length integer    not null,
  started         date       not null,
  finished        date,
  iterations      integer
);

drop table if exists backups;
create table backups (
  id            integer primary key autoincrement,
  sequence      text    not null,
  random_state  text    not null,
  saved         date    not null
);

