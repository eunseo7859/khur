-- Run once in Supabase SQL Editor. Re-running preserves existing bookings.
create table if not exists public.khur_seats (
 id text primary key
);
insert into public.khur_seats(id)
select 'R1-' || lpad(i::text,3,'0') from generate_series(1,138) i
on conflict do nothing;
insert into public.khur_seats(id)
select 'R2-' || lpad(i::text,3,'0') from generate_series(1,48) i
on conflict do nothing;
create table if not exists public.khur_bookings (
 seat_id text primary key references public.khur_seats(id),
 user_id uuid unique not null references auth.users(id) on delete cascade,
 ends_at timestamptz not null
);
alter table public.khur_seats enable row level security;
alter table public.khur_bookings enable row level security;
-- Only tightly scoped authenticated RPC functions access these tables.
revoke all on public.khur_seats from anon, authenticated;
revoke all on public.khur_bookings from anon, authenticated;

create or replace function public.khur_status()
returns jsonb language plpgsql security definer set search_path = '' as $$
declare result jsonb;
begin
 if auth.uid() is null then raise exception 'Authentication required'; end if;
 select jsonb_build_object(
   'mine',(select jsonb_build_object('seat_id',b.seat_id,'ends_at',b.ends_at)
           from public.khur_bookings b where b.user_id=auth.uid() and b.ends_at>now()),
   'occupied',coalesce((select jsonb_agg(b.seat_id) from public.khur_bookings b where b.ends_at>now()),'[]'::jsonb)
 ) into result;
 return result;
end; $$;

create or replace function public.khur_book(p_seat text)
returns jsonb language plpgsql security definer set search_path = '' as $$
declare uid uuid := auth.uid(); owner_id uuid;
begin
 if uid is null then raise exception 'Authentication required'; end if;
 -- Serialize all changes in this small demo room, including switches and returns.
 perform pg_catalog.pg_advisory_xact_lock(746821);
 if not exists(select 1 from public.khur_seats where id=p_seat) or not (p_seat ~ '^R1-(00[1-9]|0[1-9][0-9]|1[0-2][0-9]|13[0-8])$' or p_seat ~ '^R2-(00[1-9]|0[1-3][0-9]|04[0-8])$') then
  return jsonb_build_object('ok',false,'message','등록되지 않은 좌석입니다.');
 end if;
 delete from public.khur_bookings where ends_at<=now();
 select user_id into owner_id from public.khur_bookings where seat_id=p_seat;
 if owner_id is not null then
  return jsonb_build_object('ok',false,'message',case when owner_id=uid then '이미 이용 중인 내 좌석입니다.' else '다른 이용자가 먼저 등록했습니다. 기존 좌석은 유지됩니다.' end);
 end if;
 delete from public.khur_bookings where user_id=uid;
 insert into public.khur_bookings(seat_id,user_id,ends_at) values(p_seat,uid,now()+interval '2 hours');
 return jsonb_build_object('ok',true,'message',p_seat || ' 좌석 등록이 완료되었습니다.');
end; $$;

create or replace function public.khur_release()
returns jsonb language plpgsql security definer set search_path = '' as $$
begin
 if auth.uid() is null then raise exception 'Authentication required'; end if;
 perform pg_catalog.pg_advisory_xact_lock(746821);
 delete from public.khur_bookings where user_id=auth.uid();
 return jsonb_build_object('ok',true);
end; $$;
revoke all on function public.khur_status() from public, anon;
revoke all on function public.khur_book(text) from public, anon;
revoke all on function public.khur_release() from public, anon;
grant execute on function public.khur_status() to authenticated;
grant execute on function public.khur_book(text) to authenticated;
grant execute on function public.khur_release() to authenticated;
