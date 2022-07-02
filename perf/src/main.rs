use std::{
    fmt,
    fs::File,
    io::{self, BufRead},
    time::Duration,
};

use tokio::time;

#[derive(Debug)]
struct DiskStat {
    rd_ios: usize,
    rd_sec: usize,
    wr_ios: usize,
    wr_sec: usize,
}

#[tokio::main]
async fn main() -> io::Result<()> {
    let mut interval = time::interval(Duration::from_secs(1));
    let instant = interval.tick().await;
    let stat = read_diskstats_io()?;
    let first_instant = instant;
    let mut last_stat = stat;
    loop {
        let instant = interval.tick().await;
        print!("{} ", (instant - first_instant).as_millis());
        let stat = read_diskstats_io()?;
        println!("{}", stat.diff(&last_stat));
        last_stat = stat;
    }
}

/**
 * Read I/O and transfer rates statistics from /proc/diskstats.
 * cf. https://www.kernel.org/doc/Documentation/ABI/testing/procfs-diskstats
 */
fn read_diskstats_io() -> io::Result<DiskStat> {
    let file = File::open("/proc/diskstats")?;
    let reader = io::BufReader::new(file);
    for line in reader.lines() {
        let line = line.unwrap();
        let mut iter = line.split_ascii_whitespace();
        iter.next().unwrap();
        iter.next().unwrap();
        let dev_name = iter.next().unwrap();
        if dev_name != "sdb" {
            continue;
        }
        let rd_ios: usize = iter.next().unwrap().parse().unwrap();
        iter.next().unwrap();
        let rd_sec: usize = iter.next().unwrap().parse().unwrap();
        iter.next().unwrap();
        let wr_ios: usize = iter.next().unwrap().parse().unwrap();
        iter.next().unwrap();
        let wr_sec: usize = iter.next().unwrap().parse().unwrap();
        let stat = DiskStat {
            rd_ios,
            rd_sec,
            wr_ios,
            wr_sec,
        };
        return Ok(stat);
    }
    Err(io::Error::new(
        io::ErrorKind::NotFound,
        "device sdb not found",
    ))
}

impl DiskStat {
    fn diff(&self, other: &Self) -> Self {
        Self {
            rd_ios: self.rd_ios - other.rd_ios,
            rd_sec: self.rd_sec - other.rd_sec,
            wr_ios: self.wr_ios - other.wr_ios,
            wr_sec: self.wr_sec - other.wr_sec,
        }
    }
}

impl fmt::Display for DiskStat {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(
            f,
            "{} {} {} {}",
            self.rd_ios, self.rd_sec, self.wr_ios, self.wr_sec
        )
    }
}
