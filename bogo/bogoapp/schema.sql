-- Sequence being bogosorted.
drop table if exists bogos;
create table bogos (
  id       integer    primary key autoincrement,
  sequence text       not null,
  created  timestamp  not null,
  finished timestamp,
  shuffles integer
);

-- Python random builtin module state.
drop table if exists random;
create table random (
  id       integer    primary key,
  state    text,
  saved    timestamp,
  bogo     integer,
  foreign key(bogo) references bogos(id)
);

-- Instead of creating a new row for each (large)
-- random module state, rotate new values over 10 rows.
insert into random values(1, null, null, null);
insert into random values(2, null, null, null);
insert into random values(3, null, null, null);
insert into random values(4, null, null, null);
insert into random values(5, null, null, null);
insert into random values(6, null, null, null);
insert into random values(7, null, null, null);
insert into random values(8, null, null, null);
insert into random values(9, null, null, null);
insert into random values(10, null, null, null);
