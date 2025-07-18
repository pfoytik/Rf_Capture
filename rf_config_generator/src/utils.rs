#[derive(Debug, Clone, serde::Deserialize, serde::Serialize)]
#[serde(transparent)]
pub struct TimeSortedContainer<T> {
    pub val: T,
    #[serde(skip, default="default_instant")]
    time: std::time::Instant,
}

fn default_instant() -> std::time::Instant {
    std::time::Instant::now()
}

impl<'de, T: serde::Serialize + serde::Deserialize<'de>>  From<T> for TimeSortedContainer<T> {
    fn from(value: T) -> Self {
        Self {
            val: value,
            time: std::time::Instant::now(),
        }
    }
}

impl<T> PartialEq for TimeSortedContainer<T> {
    fn eq(&self, other: &Self) -> bool {
        self.time.eq(&other.time)
    }
}

impl<T> Eq for TimeSortedContainer<T> {}

impl<T> PartialOrd for TimeSortedContainer<T> {
    fn partial_cmp(&self, other: &Self) -> Option<std::cmp::Ordering> {
        return self.time.partial_cmp(&other.time) 
    }
}

impl<T> Ord for TimeSortedContainer<T> {
    fn cmp(&self, other: &Self) -> std::cmp::Ordering {
        return self.time.cmp(&other.time) 
    }
}

impl<T: Default> Default for TimeSortedContainer<T> {
    fn default() -> Self {
        Self {
            val: T::default(),
            time: std::time::Instant::now(),
        }
    }
}


pub fn rand_name<F: Fn(&String) -> bool>(test: F) -> String{
    let mut rand_byte: u8 = rand::random();
    let mut rand_name = format!("group_{:x}", rand_byte);
    while test(&rand_name) {
        rand_byte = rand::random();
        rand_name = format!("group_{:x}", rand_byte);
    }

    rand_name
}
