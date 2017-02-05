drop table if exists bogos;
create table bogos (
  id              integer    primary key autoincrement,
  sequence_length integer    not null,
  started         date       not null,
  random_state    text       not null,
  finished        date,
  iterations      integer
);

